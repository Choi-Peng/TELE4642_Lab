'''
Code Author: Peng, Caikun
File Name: net.py
Create Date: 16/07/2024 
Last Edit Date: 16/07/2024
Description: 
Dependencies: mininet, math, json, os
'''

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import math
import json
import os

class IPv6DisabledSwitch(OVSSwitch):
    def start(self, controllers):
        super(IPv6DisabledSwitch, self).start(controllers)
        # close IPv6
        self.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1')
        self.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1')

class ncmTopo(Topo):
    def build(self,routingTable={}):
        dpidToSwitchName = {}
        # Number of devices
        numHosts = 4
        numSwitches = 2
        numMonitor  = 1
        numSwitchToHosts = math.ceil(numHosts / numSwitches)
        numWhiteWeb  = 1
        
        # create monitor and links
        for monitorId in range(numMonitor): # create monitor(s)
            monitorDpid = f'{monitorId+1:016x}'
            monitorName = f'm{monitorId}'
            monitor = self.addSwitch(monitorName, dpid = monitorDpid)
            info(f"Created monitor {monitorName} with DPID {monitorDpid}\n")
            routingTable[monitorDpid] = []
            dpidToSwitchName[monitorDpid] = [monitorName]
            # create two hosts as servers
            localSever = self.addHost('server', ip = '10.0.0.1')
            linkMonitorToServer = self.addLink(localSever, monitor)
            routingTable[monitorDpid].append({
                "priority": 10,
                'actions':['output:1'],
                'match':{'ip,nw_dst': '10.0.0.1'},
                "table_id": 0
            })
            for whiteWebNum in range(numWhiteWeb):
                whiteWebIP = f'10.1.{monitorId}.{whiteWebNum+1}'
                whiteWeb = self.addHost(f'whiteWeb{whiteWebNum}', ip = whiteWebIP)
                linkMonitorToInternet = self.addLink(whiteWeb, monitor)
                routingTable[monitorDpid].append({
                    "priority": 10,
                    'actions':[f'output:{whiteWebNum+2}'],
                    'match':{'ip,nw_dst': whiteWebIP},
                    "table_id": 0
                })

            for switchId in range(numSwitches): # create switch(es)
                switchDpid = f'{monitorId+1:014x}{switchId+1:02x}'
                switchName = f's{switchId}'
                switch = self.addSwitch(switchName, dpid = switchDpid)
                info(f"Created switch {switchName} with DPID {switchDpid}\n")
                routingTable[switchDpid] = []
                dpidToSwitchName[switchDpid] = [switchName]
                # create link between monitor and switch
                linkMonitorToSwitch = self.addLink(switch, monitor)
                routingTable[monitorDpid].append({
                    "priority": 10,
                    'actions':[f'output:{switchId+whiteWebNum+3}'],
                    'match':{'ip,nw_dst': f'10.0.{switchId}.0/24'},
                    "table_id": 0
                })
                routingTable[switchDpid].append({
                    "priority": 1,
                    'actions':['output:1'],
                    'match':{},
                    "table_id": 0
                })

                for hostId in range(numSwitchToHosts): # create host(s)
                    hostIp = f'10.0.{switchId}.{hostId+2}' 
                    hostName = f'h{switchId}{hostId}'
                    host = self.addHost(hostName, ip = hostIp)
                    # create link between switch and host
                    linkHostToSwitch = self.addLink(host, switch)
                    routingTable[switchDpid].append({
                        "priority": 10,
                        'actions':[f'output:{hostId+2}'],
                        'match':{'ip,nw_dst': hostIp},
                        "table_id": 0
                    })

                    # check the number of created host
                    numHostCreated = switchId * numSwitchToHosts + hostId + 1
                    if numHostCreated == numHosts:
                        break
        
        with open('routing_table.json', 'w') as file:
            json.dump(routingTable, file, indent = 2)
        with open('dpidToSwitchName.json', 'w') as file:
            json.dump(dpidToSwitchName, file, indent = 2)

def main():
    routingTable = {}
    topo = ncmTopo(routingTable)

    net = Mininet(
        topo = topo, 
        link = TCLink, 
        switch = IPv6DisabledSwitch,
        controller = None,
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

    for host in net.hosts:
        host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1')
        host.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1')
        host.cmd('sysctl -w net.ipv6.conf.lo.disable_ipv6=1')

    configureSwitches(net,routingTable)

    CLI(net)

    net.stop()
    os.system('mn -c')

def configureSwitches(net,routingTable):
    num_switches = len(net.switches)
    for switch in net.switches:
        switch_name = switch.name
        # for that using WSL
        set_br = f'ovs-vsctl set bridge {switch_name} datapath_type=netdev'
        switch.cmd(set_br)
        switch_dpid = switch.dpid
        for route in routingTable[switch_dpid]:
            priority = route['priority']
            actions = ",".join(route["actions"])
            match = route['match']
            table_id = route['table_id']
            match_str = ",".join([f"{key}={value}" for key, value in match.items()])
            set_route = f'ovs-ofctl add-flow {switch_name} "table={table_id},priority={priority},{match_str},actions={actions}"'
            os.system(set_route)

if __name__ == '__main__':
    setLogLevel('info')
    main()