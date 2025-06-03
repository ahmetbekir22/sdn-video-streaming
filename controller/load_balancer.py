#!/usr/bin/env python3

import random
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum
import logging
import time

class LoadBalancingAlgorithm(Enum):
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    BANDWIDTH_AWARE = "bandwidth_aware"
    REQUEST_DEMAND = "request_demand"

@dataclass
class Server:
    id: str
    ip: str
    weight: int = 1
    current_connections: int = 0
    bandwidth_usage: float = 0.0
    last_request_time: float = 0.0
    video_quality: str = "auto"  # auto, 320p, 480p, 720p
    response_time: float = 0.0

class LoadBalancer:
    def __init__(self, algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN):
        self.algorithm = algorithm
        self.servers: List[Server] = []
        self.current_index = 0
        self.server_stats: Dict[str, Dict] = {}
        self.quality_weights = {
            "320p": 1,
            "480p": 2,
            "720p": 3
        }

    def add_server(self, server: Server):
        """Add a new server to the load balancer."""
        self.servers.append(server)
        self.server_stats[server.id] = {
            'requests_handled': 0,
            'total_bandwidth': 0,
            'average_response_time': 0,
            'video_qualities': {
                "320p": 0,
                "480p": 0,
                "720p": 0
            }
        }

    def remove_server(self, server_id: str):
        """Remove a server from the load balancer."""
        self.servers = [s for s in self.servers if s.id != server_id]
        if server_id in self.server_stats:
            del self.server_stats[server_id]

    def get_next_server(self) -> Server:
        """Get the next server based on the selected algorithm."""
        if not self.servers:
            raise ValueError("No servers available")

        if self.algorithm == LoadBalancingAlgorithm.RANDOM:
            return random.choice(self.servers)
        
        elif self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            server = self.servers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.servers)
            return server
        
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            # Sort servers by weight and current connections
            sorted_servers = sorted(self.servers, 
                                  key=lambda x: (x.current_connections / x.weight))
            return sorted_servers[0]
        
        elif self.algorithm == LoadBalancingAlgorithm.BANDWIDTH_AWARE:
            # Choose server with lowest bandwidth usage
            return min(self.servers, key=lambda x: x.bandwidth_usage)
        
        elif self.algorithm == LoadBalancingAlgorithm.REQUEST_DEMAND:
            # Choose server with least current connections and best response time
            return min(self.servers, 
                      key=lambda x: (x.current_connections, x.response_time))
        
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")

    def update_server_stats(self, server_id: str, bandwidth: float, response_time: float, 
                          video_quality: str = "auto"):
        """Update server statistics after handling a request."""
        if server_id in self.server_stats:
            stats = self.server_stats[server_id]
            server = next(s for s in self.servers if s.id == server_id)
            
            # Update basic stats
            stats['requests_handled'] += 1
            stats['total_bandwidth'] += bandwidth
            stats['average_response_time'] = (
                (stats['average_response_time'] * (stats['requests_handled'] - 1) + response_time)
                / stats['requests_handled']
            )
            
            # Update video quality stats
            if video_quality != "auto":
                stats['video_qualities'][video_quality] += 1
            
            # Update server object
            server.current_connections += 1
            server.bandwidth_usage += bandwidth
            server.response_time = response_time
            server.last_request_time = time.time()
            server.video_quality = video_quality
            
            logging.info(f"Updated stats for {server_id}: "
                        f"connections={server.current_connections}, "
                        f"bandwidth={server.bandwidth_usage:.2f}MB/s, "
                        f"response_time={server.response_time:.2f}ms")

    def get_server_stats(self) -> Dict:
        """Get current statistics for all servers."""
        return self.server_stats

    def get_optimal_quality(self, server_id: str) -> str:
        """Determine optimal video quality based on server stats."""
        if server_id not in self.server_stats:
            return "auto"
            
        stats = self.server_stats[server_id]
        server = next(s for s in self.servers if s.id == server_id)
        
        # If server is under heavy load, suggest lower quality
        if server.current_connections > 5 or server.bandwidth_usage > 10:
            return "320p"
        
        # If server has good response time and low load, suggest higher quality
        if server.response_time < 100 and server.current_connections < 3:
            return "720p"
        
        # Default to medium quality
        return "480p"

    def cleanup_old_connections(self, timeout: int = 300):
        """Clean up old connections that haven't been active."""
        current_time = time.time()
        for server in self.servers:
            if (current_time - server.last_request_time) > timeout:
                server.current_connections = max(0, server.current_connections - 1)
                logging.info(f"Cleaned up old connection for {server.id}") 