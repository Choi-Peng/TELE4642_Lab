'''
Code Author: Peng, Caikun
File Name: net.py
Create Date: 16/07/2024 
Last Edit Date: 16/07/2024
Description: 
Dependencies: mininet, math
'''

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import math

class ncmTopo(Topo):
    def build(self):
        # Number of devices
        numHosts = 10
        numSwitches = 1
        numMonitor  = 1
        numSwitchToHosts = math.ceil(numHosts / numSwitches)
        
        # create monitor and links
        for monitorId in range(numMonitor): # create monitor(s)
            monitorDpid = f'{monitorId:x}'
            monitorName = f'm{monitorId}'
            monitor = self.addSwitch(monitorName, dpid = monitorDpid)
            
            for switchId in range(numSwitches): # create switch(es)
                switchDpid = f'{switchId:x}'
                switchName = f's{switchId}'
                switch = self.addSwitch(switchName, dpid = switchDpid)
                # create link between monitor and switch
                linkMonitorToSwitch = self.addLink(switch, monitor)
                
                for hostId in range(numSwitchToHosts): # create host(s)
                    hostIp = f'10.0.{switchId}.{hostId+2}' 
                    hostName = f'h{switchId}{hostId}'
                    host = self.addHost(hostName, ip = hostIp)
                    # create link between switch and host
                    link = self.addLink(host, switch)

                    # check the number of created host
                    numHostCreated = switchId * numSwitchToHosts + hostId
                    if numHostCreated == numHosts:
                        break

def main():
    topo = ncmTopo()

    net = Mininet(
        topo = topo, 
        link = TCLink, 
        controller = RemoteController, 
        autoSetMacs = True, 
        autoStaticArp = True
    )

    net.addController(
        'Ctl0', 
        controller = RemoteController, 
        ip = '127.0.0.1', 
        port = 6653,
        protocols = "OpenFlow13"
    )

    net.start()

    # for that using WSL
    configureSwitches(net)

    CLI(net)

    net.stop()

def configureSwitches(net):
    num_switches = len(net.switches)
    for switch in net.switches:
        switch_name = switch.name
        set_br = f'ovs-vsctl set bridge {switch_name} datapath_type=netdev'
        switch.cmd(set_br)


if __name__ == '__main__':
    setLogLevel('info')
    main()