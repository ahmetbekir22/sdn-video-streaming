#!/usr/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class CustomTopology(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        core = [self.addSwitch(f's{i}') for i in range(2, 5)]  # s2, s3, s4
        leaf = [self.addSwitch(f's{i}') for i in range(5, 8)]  # s5, s6, s7
        servers = [self.addHost(f'server{i}', ip=f'10.0.{i}.2/24') for i in range(1, 5)]
        client = self.addHost('client', ip='10.0.0.2/24')

        for c in core:
            self.addLink(s1, c)

        for i, c in enumerate(core):
            self.addLink(c, leaf[i])
            if i < len(core) - 1:
                self.addLink(c, leaf[i + 1])

        for i, srv in enumerate(servers):
            self.addLink(srv, leaf[i % len(leaf)])

        self.addLink(client, s1)

topos = {'customtopology': CustomTopology}

def run():
    topo = CustomTopology()
    net = Mininet(topo=topo, controller=None)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    net.start()

    for i in range(1, 5):
        net.get(f'server{i}').cmd(f'cd /home/mininet/www && python3 -m http.server 8000 &')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()

