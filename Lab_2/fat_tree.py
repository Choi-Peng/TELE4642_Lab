'''
Code Author: Peng, Caikun
File Name: fat_tree.py
Create Date: 16/06/2024 
Last Edit Date: 19/06/2024
Description: Generate fat-tree topo with parameter k
Dependencies: argparse, mininet, json
'''

import argparse
from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import json

def main(k):
    net = Mininet(controller = RemoteController,
                      switch = OVSSwitch,
                        link = TCLink)

    net.addController('Ctl0', controller = RemoteController, 
                                      ip = '127.0.0.1', 
                                    port = 6653)

    switches_aggr = []
    hosts         = []
    routing_table = {}
    priority_down = 100
    priority_up   = 10
    dpid_switch   = {}

    # create edge switches, arrg switches, hosts and links 
    for pod in range(k):
        pod_switches_edge = []
        pod_switches_aggr = []
        # edge switches and host with links
        for i in range(k//2): 
            # create edge switch
            switch_num  = i
            switch_id   = i
            switch_dpid = f'0000000000{pod:02x}{switch_num:02x}01'
            switch_name = f'edSw{pod}{switch_id}'
            dpid_switch[switch_dpid] = switch_name
            info(f'Creating edge switch {switch_name}\n')
            switch_edge = net.addSwitch(switch_name, 
                                        dpid = switch_dpid)
            pod_switches_edge.append(switch_edge)
            routing_table[switch_name] = { # initial routing table
                "routes": [], 
                "suffix_routes": []
            }
            # create host
            for host_id in range (k // 2):
                host_name = f'h{pod}{switch_id}{host_id}'
                host_ip   = f'10.{pod}.{switch_id}.{host_id+2}'
                info(f'Creating host {host_name}\n')
                host      = net.addHost(host_name, ip = host_ip)
                # create links between edge switch and host
                net.addLink(host, switch_edge)
                # add ronte rules for edge switches
                route = {
                    "prefix"   : host_ip,
                    "mask"     : 0xffffffff,
                    "priority" : priority_down,
                    "output"   : host_id + 1
                }
                suffix_route = {
                    "suffix"   : host_ip,
                    "mask"     : 0x000000ff, 
                    "priority" : priority_up, 
                    "output"   : host_id + 1 + (k // 2)
                }
                routing_table[switch_name]["routes"].append(route)
                routing_table[switch_name]["suffix_routes"].append(suffix_route)

            
        # create aggr switches with links
        for i in range(k//2): 
            # create aggr switch
            switch_num  = (k // 2) + i
            switch_id   = i
            switch_dpid = f'0000000000{pod:02x}{switch_num:02x}01'
            switch_name = f'agSw{pod}{switch_id}'
            dpid_switch[switch_dpid] = switch_name
            info(f'Creating aggr switch {switch_name}\n')
            switch_aggr = net.addSwitch(switch_name, 
                                        dpid = switch_dpid)
            pod_switches_aggr.append(switch_aggr)
            # create links between aggr switch and edge switch
            for switch_edge in pod_switches_edge:
                net.addLink(switch_aggr, switch_edge)
            # add ronte rules for aggr switches
            routing_table[switch_name] = { # initial routing table
                "routes": [], 
                "suffix_routes": []
            }
            for host_id in range (k // 2):
                route = {
                    "prefix"   : f'10.{pod}.{host_id}.0',
                    "mask"     : 0xffffff00,
                    "priority" : priority_down,
                    "output"   : host_id + 1
                }
                suffix_route = {
                    "suffix"   : f'10.{pod}.{host_id}.0',
                    "mask"     : 0x0000ff00, 
                    "priority" : priority_up, 
                    "output"   : host_id + 1 + (k // 2)
                }
                routing_table[switch_name]["routes"].append(route)
                routing_table[switch_name]["suffix_routes"].append(suffix_route)
        switches_aggr.append(pod_switches_aggr)

    # create core switches and links
    # create core switches
    for j in range(k//2):
        for i in range(k//2):
            switch_id   = (j*(k//2))+i
            switch_dpid = f'0000000000{k:02x}{j:02x}{i:02x}'
            switch_name = f'crSw{switch_id}'
            dpid_switch[switch_dpid] = switch_name
            info(f'Creating core switch {switch_name}\n')
            switch_core = net.addSwitch(switch_name, 
                                        dpid = switch_dpid)
            for num  in range(k):
                net.addLink(switches_aggr[num][j], switch_core) 
            # add ronte rules for core switches
            routing_table[switch_name] = { # initial routing table
                "routes": []
            }
            for pod in range(k):
                route = {
                    "prefix"   : f'10.{pod}.0.0',
                    "mask"     : 0xffff0000,
                    "priority" : priority_down,
                    "output"   : pod + 1
                }
                routing_table[switch_name]["routes"].append(route)

    with open('routing_table.json', 'w') as f:
        json.dump(routing_table, f, indent=4)
    with open('dpid_switch_table.json', 'w') as f:
        json.dump(dpid_switch, f , indent=4)

    net.build()

    ip_mac_table = {}
    for host in net.hosts:
        ip_mac_table[host.IP()] = host.MAC()
    
    with open('ip_mac_table.json', 'w') as f:
        json.dump(ip_mac_table, f,indent=4)

    net.start()

    configure_switches(net, k)

    CLI(net)
    net.stop()

def configure_switches(net, k):
    info('*** Configuring switches...')
    num_switches = len(net.switches)
    
    with open('swconfig', 'w') as swconfig:
        for switch in net.switches:
            switch_name = switch.name
            info(f'*** Configuring {switch_name}\n')
            set_br = f'ovs-vsctl set bridge {switch_name} datapath_type=netdev'
            switch.cmd(set_br)
            swconfig.write(f'sh {set_br}\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, 
                          default=4, 
                             help="k order of fat-tree topo")
    args = parser.parse_args()
    k = args.k
    setLogLevel('info')
    main(k)