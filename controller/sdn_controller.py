#!/usr/bin/env python3

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp
from ryu.lib import hub
import json
import logging
from load_balancer import LoadBalancer, Server, LoadBalancingAlgorithm

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
        
        # Initialize load balancer
        self.load_balancer = LoadBalancer(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)
        
        # Add video servers
        self.servers = [
            Server(id=f'server{i}', ip=f'10.0.{i}.2', weight=1)
            for i in range(1, 5)
        ]
        for server in self.servers:
            self.load_balancer.add_server(server)
        
        # Store switch information
        self.switches = {}
        self.mac_to_port = {}
        
        # Start monitoring thread
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch features event."""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Store switch information
        self.switches[datapath.id] = datapath
        self.mac_to_port[datapath.id] = {}

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Add a flow entry to the switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                           actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match,
                                  instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Handle packet in events."""
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

        # Check if this is an IP packet
        ip_header = pkt.get_protocol(ipv4.ipv4)
        if ip_header:
            # Check if this is a TCP packet
            tcp_header = pkt.get_protocol(tcp.tcp)
            if tcp_header and tcp_header.dst_port == 8000:  # HTTP port
                # This is a video streaming request
                self._handle_video_request(datapath, in_port, ip_header, tcp_header)
                return

        # Handle other packets (ARP, etc.)
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        
        # Install flow entry
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions)
        datapath.send_msg(out)

    def _handle_video_request(self, datapath, in_port, ip_header, tcp_header):
        """Handle video streaming requests."""
        parser = datapath.ofproto_parser
        
        # Get next server using load balancer
        try:
            server = self.load_balancer.get_next_server()
            logging.info(f"Selected server {server.id} for request from {ip_header.src}")
            
            # Create flow entry for this connection
            match = parser.OFPMatch(
                eth_type=0x0800,  # IPv4
                ipv4_src=ip_header.src,
                ipv4_dst=ip_header.dst,
                ip_proto=6,  # TCP
                tcp_src=tcp_header.src_port,
                tcp_dst=tcp_header.dst_port
            )
            
            # Forward to selected server
            actions = [parser.OFPActionOutput(self.mac_to_port[datapath.id][server.ip])]
            self.add_flow(datapath, 2, match, actions)
            
            # Update server statistics
            self.load_balancer.update_server_stats(server.id, 0, 0)  # Initial stats
            
        except ValueError as e:
            logging.error(f"Error selecting server: {str(e)}")
            # Flood the packet if no server is available
            actions = [parser.OFPActionOutput(datapath.ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions
            )
            datapath.send_msg(out)

    def _monitor(self):
        """Monitor thread for collecting statistics."""
        while True:
            for dp in self.switches.values():
                self._request_stats(dp)
            hub.sleep(10)  # Collect stats every 10 seconds

    def _request_stats(self, datapath):
        """Request flow and port statistics from switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        """Handle flow statistics reply."""
        body = ev.msg.body
        logging.info('Flow Stats:')
        for stat in body:
            logging.info(f'Match: {stat.match}, '
                        f'Packets: {stat.packet_count}, '
                        f'Bytes: {stat.byte_count}')

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        """Handle port statistics reply."""
        body = ev.msg.body
        logging.info('Port Stats:')
        for stat in body:
            logging.info(f'Port: {stat.port_no}, '
                        f'Rx Bytes: {stat.rx_bytes}, '
                        f'Tx Bytes: {stat.tx_bytes}') 