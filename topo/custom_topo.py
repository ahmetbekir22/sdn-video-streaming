#!/usr/bin/env python3
# This is the custom topology for the SDN video streaming with load balancing
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class LinuxRouter(Node):
    """A Node with IP forwarding enabled."""
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

class CustomTopology(Topo):
    """Custom topology for SDN video streaming with load balancing."""
    
    def build(self, **_opts):
        # Create switches
        border_switch = self.addSwitch('s1')
        core_switches = [self.addSwitch(f's{i}') for i in range(2, 5)]  # s2, s3, s4
        leaf_switches = [self.addSwitch(f's{i}') for i in range(5, 8)]   # s5, s6, s7
        
        # Create video servers
        servers = []
        for i in range(1, 5):
            server = self.addHost(f'server{i}', ip=f'10.0.{i}.2/24')
            servers.append(server)
        
        # Create client
        client = self.addHost('client', ip='10.0.0.2/24')
        
        # Add links between switches
        # Border switch to core switches
        for core_switch in core_switches:
            self.addLink(border_switch, core_switch)
        
        # Core switches to leaf switches
        for i, core_switch in enumerate(core_switches):
            self.addLink(core_switch, leaf_switches[i])
            if i < len(core_switches) - 1:
                self.addLink(core_switch, leaf_switches[i + 1])
        
        # Connect servers to leaf switches
        for i, server in enumerate(servers):
            self.addLink(server, leaf_switches[i % len(leaf_switches)])
        
        # Connect client to border switch
        self.addLink(client, border_switch)

def run():
    """Test the custom topology."""
    topo = CustomTopology()
    net = Mininet(topo=topo, controller=None, waitConnected=True)
    
    # Add remote controller
    net.addController('c0', controller=RemoteController, ip="127.0.0.1", port=6653)

    info('*** Starting network\n')
    net.start()
    
    # Start HTTP servers on video servers
    for i in range(1, 5):
        server = net.get(f'server{i}')
        server.cmd('cd /home/mininet/se3506 && python3 -m http.server 8000 &')
    
    # Start Chrome on client
    client = net.get('client')
    client.cmd('xterm -e google-chrome --kiosk --no-sandbox --autoplay-policy=no-user-gesture-required --app=http://10.0.1.2:8000/index.html &')
    
    info('*** Running CLI\n')
    CLI(net)
    
    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run() 