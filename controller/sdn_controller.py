#!/usr/bin/env python3

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, arp
from ryu.lib import hub
import logging
from load_balancer import LoadBalancer, Server, LoadBalancingAlgorithm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler('controller.log'), logging.StreamHandler()]
)

class VideoStreamingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(VideoStreamingController, self).__init__(*args, **kwargs)
        # Load balancer
        self.lb = LoadBalancer(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)
        for i in range(1, 5):
            self.lb.add_server(Server(id=f'server{i}', ip=f'10.0.{i}.2', weight=1))
        # State
        self.switches = {}
        self.mac_to_port = {}
        self.ip_to_mac = {}
        # Stats thread
        hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser

        # Initialize per‐switch maps
        self.switches[dp.id]   = dp
        self.mac_to_port[dp.id] = {}
        self.ip_to_mac[dp.id]   = {}

        # 0) ARP → flood (en yüksek öncelik)
        self.add_flow(dp, 4,
                      parser.OFPMatch(eth_type=0x0806),
                      [parser.OFPActionOutput(ofp.OFPP_FLOOD)])
        # 1) ICMP → flood (öncelik 3)
        self.add_flow(dp, 3,
                      parser.OFPMatch(eth_type=0x0800, ip_proto=1),
                      [parser.OFPActionOutput(ofp.OFPP_FLOOD)])
        # 2) ARP → controller (öncelik 2)
        self.add_flow(dp, 2,
                      parser.OFPMatch(eth_type=0x0806),
                      [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)])
        # 3) Default → controller
        self.add_flow(dp, 0,
                      parser.OFPMatch(),
                      [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)])

        logging.info(f"Switch {dp.id} ready")

    def add_flow(self, dp, prio, match, actions, buffer_id=None, idle_timeout=0, hard_timeout=0):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id is not None:
            mod = parser.OFPFlowMod(dp, buffer_id=buffer_id, priority=prio,
                                    match=match, instructions=inst,
                                    idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(dp, priority=prio,
                                    match=match, instructions=inst,
                                    idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg, dp = ev.msg, ev.msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser
        in_port, dpid = msg.match['in_port'], dp.id

        # Ensure maps exist
        if dpid not in self.mac_to_port:
            self.mac_to_port[dpid] = {}
            self.ip_to_mac[dpid]   = {}

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        src, dst = eth.src, eth.dst

        # Learn MAC
        self.mac_to_port[dpid][src] = in_port

        # ARP?
        if pkt.get_protocol(arp.arp):
            return self._handle_arp(dp, in_port, msg)

        # IPv4?
        ip_hdr = pkt.get_protocol(ipv4.ipv4)
        if ip_hdr:
            # Learn IP→MAC
            self.ip_to_mac[dpid][ip_hdr.src] = src
            # Video TCP?
            tcp_hdr = pkt.get_protocol(tcp.tcp)
            if tcp_hdr and tcp_hdr.dst_port == 8000:
                return self._handle_video_request(dp, in_port, ip_hdr, tcp_hdr, msg)

        # Default switching
        return self._handle_normal_switching(dp, in_port, msg)

    def _handle_arp(self, dp, port, msg):
        ofp, parser, dpid = dp.ofproto, dp.ofproto_parser, dp.id
        pkt = packet.Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp.arp)

        # Learn ARP
        self.ip_to_mac[dpid][arp_pkt.src_ip] = arp_pkt.src_mac
        self.mac_to_port[dpid][arp_pkt.src_mac] = port

        if arp_pkt.opcode == arp.ARP_REQUEST:
            tgt_mac = self.ip_to_mac[dpid].get(arp_pkt.dst_ip)
            if tgt_mac:
                # Send ARP reply
                reply = packet.Packet()
                reply.add_protocol(ethernet.ethernet(
                    ethertype=0x0806, src=tgt_mac, dst=arp_pkt.src_mac))
                reply.add_protocol(arp.arp(
                    opcode=arp.ARP_REPLY,
                    src_mac=tgt_mac, src_ip=arp_pkt.dst_ip,
                    dst_mac=arp_pkt.src_mac, dst_ip=arp_pkt.src_ip))
                reply.serialize()
                data = reply.data
                actions = [parser.OFPActionOutput(port)]
            else:
                data = msg.data
                actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
        else:
            data = msg.data
            actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]

        out = parser.OFPPacketOut(dp,
                                  buffer_id=ofp.OFP_NO_BUFFER,
                                  in_port=ofp.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        dp.send_msg(out)

    def _handle_normal_switching(self, dp, port, msg):
        ofp, parser, dpid = dp.ofproto, dp.ofproto_parser, dp.id
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst, src = eth.dst, eth.src

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            actions = [parser.OFPActionOutput(out_port)]
            match = parser.OFPMatch(in_port=port, eth_src=src, eth_dst=dst)
            self.add_flow(dp, 1, match, actions, idle_timeout=10)
            data = msg.data
        else:
            actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            data = msg.data

        out = parser.OFPPacketOut(dp,
                                  buffer_id=ofp.OFP_NO_BUFFER,
                                  in_port=port,
                                  actions=actions,
                                  data=data)
        dp.send_msg(out)

    def _handle_video_request(self, dp, port, ip_hdr, tcp_hdr, msg):
        ofp, parser, dpid = dp.ofproto, dp.ofproto_parser, dp.id
        srv = self.lb.get_next_server()
        srv_mac = self.ip_to_mac[dpid].get(srv.ip)
        srv_port = self.mac_to_port[dpid].get(srv_mac)
        if not srv_mac or not srv_port:
            actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            data = msg.data
        else:
            match = parser.OFPMatch(
                eth_type=0x0800, ip_proto=6,
                ipv4_src=ip_hdr.src, ipv4_dst=ip_hdr.dst,
                tcp_src=tcp_hdr.src_port, tcp_dst=tcp_hdr.dst_port
            )
            actions = [
                parser.OFPActionSetField(ipv4_dst=srv.ip),
                parser.OFPActionSetField(eth_dst=srv_mac),
                parser.OFPActionOutput(srv_port)
            ]
            self.add_flow(dp, 10, match, actions, idle_timeout=30, hard_timeout=300)
            data = msg.data

        out = parser.OFPPacketOut(dp,
                                  buffer_id=ofp.OFP_NO_BUFFER,
                                  in_port=port,
                                  actions=actions,
                                  data=data)
        dp.send_msg(out)

    def _monitor(self):
        while True:
            for dp in self.switches.values():
                dp.send_msg(dp.ofproto_parser.OFPFlowStatsRequest(dp))
                dp.send_msg(dp.ofproto_parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY))
            hub.sleep(10)
