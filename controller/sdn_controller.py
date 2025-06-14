#!/usr/bin/env python3

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, arp
from ryu.lib import hub

import logging
from controller.load_balancer import LoadBalancer, Server, LoadBalancingAlgorithm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('controller.log'),
        logging.StreamHandler()
    ]
)

class VideoStreamingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(VideoStreamingController, self).__init__(*args, **kwargs)

        self.load_balancer = LoadBalancer(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)
        self.servers = [
            Server(id=f'server{i}', ip=f'10.0.{i}.2', weight=1)
            for i in range(1, 5)
        ]
        for server in self.servers:
            self.load_balancer.add_server(server)

        self.switches = {}
        self.mac_to_port = {}
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        match = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        self.add_flow(datapath, 1, match, [parser.OFPActionOutput(ofproto.OFPP_FLOOD)])

        match = parser.OFPMatch(eth_type=0x0806)
        self.add_flow(datapath, 1, match, [parser.OFPActionOutput(ofproto.OFPP_FLOOD)])

        self.switches[datapath.id] = datapath
        self.mac_to_port[datapath.id] = {}

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        print(">>> PACKET_IN geldi")

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port[dpid][src] = in_port

        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            self._handle_arp(datapath, in_port, eth, arp_pkt)
            return

        ip_header = pkt.get_protocol(ipv4.ipv4)
        tcp_header = pkt.get_protocol(tcp.tcp)

        if not ip_header:
            print(">>> IP paketi yok")
        else:
            print(f">>> IP paketi: {ip_header.src} -> {ip_header.dst}")

        if not tcp_header:
            print(">>> TCP paketi yok")
        else:
            print(f">>> TCP paketi: src={tcp_header.src_port}, dst={tcp_header.dst_port}")

        if tcp_header and tcp_header.dst_port == 8000:
            self._handle_video_request(datapath, in_port, ip_header, tcp_header)
            return

        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions)
        datapath.send_msg(out)

    def _handle_arp(self, datapath, in_port, eth, arp_pkt):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        if arp_pkt.opcode == arp.ARP_REQUEST:
            target_ip = arp_pkt.dst_ip
            target_mac = None
            for dpid, mac_port in self.mac_to_port.items():
                for mac, port in mac_port.items():
                    if mac == target_ip:
                        target_mac = mac
                        break

            if target_mac:
                arp_reply = packet.Packet()
                arp_reply.add_protocol(ethernet.ethernet(ethertype=eth.ethertype,
                                                         dst=eth.src,
                                                         src=target_mac))
                arp_reply.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                               src_mac=target_mac,
                                               src_ip=target_ip,
                                               dst_mac=eth.src,
                                               dst_ip=arp_pkt.src_ip))
                arp_reply.serialize()

                actions = [parser.OFPActionOutput(in_port)]
                out = parser.OFPPacketOut(datapath=datapath,
                                          buffer_id=ofproto.OFP_NO_BUFFER,
                                          in_port=ofproto.OFPP_CONTROLLER,
                                          actions=actions,
                                          data=arp_reply.data)
                datapath.send_msg(out)
            else:
                actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                out = parser.OFPPacketOut(datapath=datapath,
                                          buffer_id=ofproto.OFP_NO_BUFFER,
                                          in_port=in_port,
                                          actions=actions,
                                          data=msg.data)
                datapath.send_msg(out)

        elif arp_pkt.opcode == arp.ARP_REPLY:
            self.mac_to_port[datapath.id][arp_pkt.src_mac] = in_port
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(datapath=datapath,
                                      buffer_id=ofproto.OFP_NO_BUFFER,
                                      in_port=in_port,
                                      actions=actions,
                                      data=msg.data)
            datapath.send_msg(out)

    def _handle_video_request(self, datapath, in_port, ip_header, tcp_header):
        parser = datapath.ofproto_parser

        try:
            server = self.load_balancer.get_next_server()
            logging.info(f"Selected server {server.id} for request from {ip_header.src}")

            match = parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=ip_header.src,
                ipv4_dst=ip_header.dst,
                ip_proto=6,
                tcp_src=tcp_header.src_port,
                tcp_dst=tcp_header.dst_port
            )

            out_port = self.mac_to_port[datapath.id].get(server.ip)
            if out_port is None:
                raise ValueError("No out port for server IP")

            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 2, match, actions)
            self.load_balancer.update_server_stats(server.id, 0, 0)

        except ValueError as e:
            logging.error(f"Error selecting server: {str(e)}")
            actions = [parser.OFPActionOutput(datapath.ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions
            )
            datapath.send_msg(out)

    def _monitor(self):
        while True:
            for dp in self.switches.values():
                self._request_stats(dp)
            hub.sleep(10)

    def _request_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        logging.info('Flow Stats:')
        for stat in body:
            logging.info(f'Match: {stat.match}, Packets: {stat.packet_count}, Bytes: {stat.byte_count}')

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        logging.info('Port Stats:')
        for stat in body:
            logging.info(f'Port: {stat.port_no}, Rx Bytes: {stat.rx_bytes}, Tx Bytes: {stat.tx_bytes}')

