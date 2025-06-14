#!/usr/bin/env python3
# This is the custom topology for the SDN video streaming with load balancing
# It is a 3-tier topology with 1 border switch, 3 core switches, 3 leaf switches, 5 video servers, and 1 client
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import time

class CustomTopology(Topo):
    """SDN video streaming için özel topoloji."""
    
    def build(self, **_opts):
        # Switch'leri oluştur
        s1 = self.addSwitch('s1')  # Border switch
        s2 = self.addSwitch('s2')  # Core switch
        s3 = self.addSwitch('s3')  # Leaf switch
        
        # Video sunucularını oluştur
        server1 = self.addHost('server1', ip='10.0.0.1/24')
        server2 = self.addHost('server2', ip='10.0.0.2/24')
        
        # İstemciyi oluştur
        client = self.addHost('client', ip='10.0.0.3/24')
        
        # Bağlantıları oluştur
        self.addLink(s1, s2)  # Border switch -> Core switch
        self.addLink(s2, s3)  # Core switch -> Leaf switch
        self.addLink(s3, server1)  # Leaf switch -> Server1
        self.addLink(s3, server2)  # Leaf switch -> Server2
        self.addLink(s1, client)   # Border switch -> Client

def run():
    """Topolojiyi test et."""
    topo = CustomTopology()
    net = Mininet(topo=topo, controller=None, waitConnected=True)
    
    # Ryu controller'ı ekle
    net.addController('c0', controller=RemoteController, ip="127.0.0.1", port=6653)

    info('*** Ağı başlatıyorum\n')
    net.start()
    
    # Controller'ın bağlanması için daha uzun bir süre bekle (kritik)
    time.sleep(7) 

    # Sunucularda HTTP server'ları başlat ve istemciye curl yükle
    for i in range(1, 3):
        server = net.get(f'server{i}')
        # se3506 klasörünün doğru yolu (sanal makinenizdeki /mnt/sdn-video-streaming/se3506)
        server.cmd(f'cd /mnt/sdn-video-streaming/se3506 && python3 -m http.server 8000 &')
    
    client = net.get('client')
    # curl'u yükle ve kurulumun tamamlanmasını bekle, sonra kısa bir süre daha bekle
    info('*** İstemcide curl yükleniyor...\n')
    client.cmd('sudo apt update -y > /dev/null 2>&1 && sudo apt install -y curl > /dev/null 2>&1 && sleep 3') # Çıktıyı gizle ve 3 sn bekle
    info('*** curl yüklemesi tamamlandı.\n')

    info('*** CLI başlatılıyor\n')
    CLI(net)
    
    info('*** Ağı durduruyorum\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run() 