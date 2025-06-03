#!/usr/bin/env python3

import socket
import threading
import time
import json
import logging
from typing import Dict, List
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from controller.load_balancer import LoadBalancer, Server, LoadBalancingAlgorithm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_environment.log'),
        logging.StreamHandler()
    ]
)

def find_free_port(start_port: int) -> int:
    """Find a free port starting from start_port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        port = start_port
        while port < start_port + 100:  # Try up to 100 ports
            try:
                s.bind(('', port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"Could not find a free port starting from {start_port}")

class MockSwitch:
    """Simulates a network switch."""
    def __init__(self, name: str):
        self.name = name
        self.ports: Dict[str, int] = {}  # mac -> port mapping
        self.flows: List[Dict] = []
        self.stats = {
            'packets_processed': 0,
            'bytes_processed': 0
        }

    def add_port(self, mac: str, port: int):
        self.ports[mac] = port

    def add_flow(self, match: Dict, actions: List[Dict]):
        self.flows.append({
            'match': match,
            'actions': actions,
            'timestamp': time.time()
        })

    def process_packet(self, src_mac: str, dst_mac: str, data: bytes) -> int:
        """Process a packet and return the output port."""
        self.stats['packets_processed'] += 1
        self.stats['bytes_processed'] += len(data)

        # Check flows
        for flow in self.flows:
            if self._match_flow(flow['match'], src_mac, dst_mac):
                return flow['actions'][0]['port']

        # If no flow match, flood
        return -1

    def _match_flow(self, match: Dict, src_mac: str, dst_mac: str) -> bool:
        """Check if a packet matches a flow entry."""
        if 'src_mac' in match and match['src_mac'] != src_mac:
            return False
        if 'dst_mac' in match and match['dst_mac'] != dst_mac:
            return False
        return True

class MockVideoServer(BaseHTTPRequestHandler):
    """Simulates a video streaming server."""
    def do_GET(self):
        if self.path == '/':
            self._send_video_list()
        elif self.path.startswith('/video/'):
            self._stream_video(self.path[7:])
        else:
            self.send_error(404, "File not found")

    def _send_video_list(self):
        """Send list of available videos."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        video_list = [
            {
                'name': 'bbb_320p.mp4',
                'size': 1024 * 1024 * 10,  # 10MB
                'url': '/video/bbb_320p.mp4'
            },
            {
                'name': 'bbb_480p.mp4',
                'size': 1024 * 1024 * 20,  # 20MB
                'url': '/video/bbb_480p.mp4'
            },
            {
                'name': 'bbb_720p.mp4',
                'size': 1024 * 1024 * 40,  # 40MB
                'url': '/video/bbb_720p.mp4'
            }
        ]
        
        self.wfile.write(json.dumps(video_list).encode())

    def _stream_video(self, filename: str):
        """Simulate video streaming."""
        self.send_response(200)
        self.send_header('Content-type', 'video/mp4')
        self.send_header('Content-Length', '10485760')  # 10MB
        self.end_headers()
        
        # Simulate streaming by sending chunks
        chunk_size = 8192
        total_size = 10 * 1024 * 1024  # 10MB
        sent = 0
        
        while sent < total_size:
            chunk = b'0' * min(chunk_size, total_size - sent)
            self.wfile.write(chunk)
            sent += len(chunk)
            time.sleep(0.01)  # Simulate network delay

class TestEnvironment:
    """Test environment that simulates our network topology."""
    def __init__(self):
        self.switches: Dict[str, MockSwitch] = {}
        self.servers: Dict[str, HTTPServer] = {}
        self.server_ports: Dict[str, int] = {}
        self.load_balancer = LoadBalancer(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)
        
        # Initialize switches
        self.switches['s1'] = MockSwitch('s1')  # Border switch
        for i in range(2, 5):
            self.switches[f's{i}'] = MockSwitch(f's{i}')  # Core switches
        for i in range(5, 8):
            self.switches[f's{i}'] = MockSwitch(f's{i}')  # Leaf switches

        # Initialize servers with dynamic port allocation
        for i in range(1, 5):
            try:
                # Find a free port starting from 9000
                port = find_free_port(9000 + i)
                self.server_ports[f'server{i}'] = port
                
                server = Server(id=f'server{i}', ip=f'10.0.{i}.2', weight=1)
                self.load_balancer.add_server(server)
                
                # Start HTTP server
                server_address = ('', port)
                httpd = HTTPServer(server_address, MockVideoServer)
                self.servers[f'server{i}'] = httpd
                
                # Start server in a separate thread
                thread = threading.Thread(target=httpd.serve_forever)
                thread.daemon = True
                thread.start()
                
                logging.info(f"Started server{i} on port {port}")
            except Exception as e:
                logging.error(f"Failed to start server{i}: {str(e)}")
                raise

    def simulate_request(self, client_ip: str, video_name: str):
        """Simulate a video request from a client."""
        try:
            # Get next server using load balancer
            server = self.load_balancer.get_next_server()
            logging.info(f"Selected server {server.id} for request from {client_ip}")
            
            # Simulate packet flow through switches
            src_mac = f"00:00:00:00:00:{client_ip.split('.')[-1]}"
            dst_mac = f"00:00:00:00:00:{server.ip.split('.')[-1]}"
            
            # Add flow entries
            self.switches['s1'].add_flow(
                {'src_mac': src_mac, 'dst_mac': dst_mac},
                [{'port': 1}]
            )
            
            # Process packet
            data = b'GET /video/' + video_name.encode() + b' HTTP/1.1\r\n'
            self.switches['s1'].process_packet(src_mac, dst_mac, data)
            
            # Update server stats
            self.load_balancer.update_server_stats(
                server.id,
                bandwidth=1.0,  # 1 MB/s
                response_time=50.0,  # 50ms
                video_quality=video_name.split('_')[1].split('.')[0]
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Error simulating request: {str(e)}")
            return False

    def get_stats(self) -> Dict:
        """Get statistics from all components."""
        stats = {
            'switches': {},
            'servers': self.load_balancer.get_server_stats()
        }
        
        for switch_name, switch in self.switches.items():
            stats['switches'][switch_name] = switch.stats
            
        return stats

def main():
    """Run the test environment."""
    env = TestEnvironment()
    
    # Simulate some requests
    for i in range(10):
        client_ip = f"10.0.0.{i+1}"
        video_name = f"bbb_{['320p', '480p', '720p'][i % 3]}.mp4"
        env.simulate_request(client_ip, video_name)
        time.sleep(1)
    
    # Print statistics
    print("\nTest Environment Statistics:")
    print(json.dumps(env.get_stats(), indent=2))

if __name__ == '__main__':
    main() 