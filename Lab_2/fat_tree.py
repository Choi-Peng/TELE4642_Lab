'''
Code Author: Peng, Caikun
File Name: fat_tree.py
Create Date: 16/06/2024 
Last Edit Date: 17/06/2024
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

    # create edge switches, arrg switches, hosts and links 
    for pod in range(k):
        pod_switches_edge = []
        pod_switches_aggr = []
        # edge switches and host with links
        for i in range(k//2): 
            # create edge switch
            switch_num  = i
            switch_id   = i
            switch_dpid = f'0000000000{pod}{switch_num}01'
            switch_name = f'edSw{pod}{switch_id}'
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
                host      = net.addHost(host_name, ip = host_ip)
                # create links between edge switch and host
                net.addLink(host, switch_edge)
                # add ronte rules for edge switches
                route = {
                    "prefix"     : host_ip,
                    "prefix_len" : 32,
                    "priority"   : priority_down,
                    "output"     : host_id + 1
                }
                suffix_route = {
                    "suffix"     : f'0.0.0.{host_id+2}',
                    "prefix_len" : 32, 
                    "priority"   : priority_up, 
                    "output"     : host_id + 1 + (k // 2)
                }
                routing_table[switch_name]["routes"].append(route)
                routing_table[switch_name]["suffix_routes"].append(suffix_route)

            
        # create aggr switches with links
        for i in range(k//2): 
            # create aggr switch
            switch_num  = (k // 2) + i
            switch_id   = i
            switch_dpid = f'0000000000{pod}{switch_num}01'
            switch_name = f'agSw{pod}{switch_id}'
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
                    "suffix"     : f'10.0.{host_id}.0',
                    "prefix_len" : 24,
                    "priority"   : priority_down,
                    "output"     : host_id + 1
                }
                suffix_route = {
                    "suffix"     : f'0.0.{host_id}.0',
                    "prefix_len" : 24, 
                    "priority"   : priority_up, 
                    "output"     : host_id + 1 + (k // 2)
                }
                routing_table[switch_name]["routes"].append(route)
                routing_table[switch_name]["suffix_routes"].append(suffix_route)
        switches_aggr.append(pod_switches_aggr)

    # create core switches and links
    # create core switches
    for j in range(k//2):
        for i in range(k//2):
            switch_id   = (j*(k//2))+i
            switch_dpid = f'0000000000{k}{j}{i}'
            switch_name = f'crSw{switch_id}'
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
                    "suffix"     : f'10.{pod}.0.0',
                    "prefix_len" : 16,
                    "priority"   : priority_down,
                    "output"     : pod + 1
                }
                routing_table[switch_name]["routes"].append(route)

    with open('routing_table.json', 'w') as f:
        json.dump(routing_table, f, indent=4)

    net.build()
    net.start()

    configure_switches(net, k)

    CLI(net)
    net.stop()

def configure_switches(net, k):
    print('*** Configuring switches')
    num_switches = len(net.switches)
    
    # edge and aggr switches
    for j in range(k):
        for i in range(k // 2):
            index =  (j * k) + i
            switch = net.switches[index]
            switch_name = switch.name
            print(f'*** Configuring {switch_name}')
            set_br = f'ovs-vsctl set bridge {switch_name} datapath_type=netdev'
            switch.cmd(set_br)
        for i in range(k // 2):
            index =  (j * k) + (k // 2) + i
            switch = net.switches[index]
            switch_name = switch.name
            print(f'*** Configuring {switch_name}')
            set_br = f'ovs-vsctl set bridge {switch_name} datapath_type=netdev'
            switch.cmd(set_br)

    # core switches
    for switch in net.switches[k ** 2 : ]:
        switch_name = switch.name
        print(f'*** Configuring {switch_name}')
        set_br = f'ovs-vsctl set bridge {switch_name} datapath_type=netdev'
        switch.cmd(set_br)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, 
                          default=4, 
                             help="k order of fat-tree topo")
    args = parser.parse_args()
    k = args.k
    main(k)