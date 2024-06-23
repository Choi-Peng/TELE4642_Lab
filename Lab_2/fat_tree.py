'''
Code Author: Peng, Caikun
File Name: fat_tree.py
Create Date: 16/06/2024 
Last Edit Date: 23/06/2024
Description: Generate fat-tree topo with parameter k
Dependencies: argparse, mininet, json
'''

import argparse
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import json

class fat_tree_topo(Topo):
    def build(self):
        switches_aggr = []
        hosts         = []
        routing_table = {}
        priority_down = 100
        priority_up   = 10
        dpid_switch   = {}
        swconfig      = open('swconfig', 'w')

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
                switch_edge = self.addSwitch(switch_name, 
                                            dpid = switch_dpid)
                pod_switches_edge.append(switch_edge)
                routing_table[switch_name] = { # initial routing table
                    "routes": [], 
                    "suffix_routes": []
                }
                swconfig.write(f'sh ovs-vsctl set bridge {switch_name} datapath_type=netdev\n')
                # create host
                for host_id in range (k // 2):
                    host_name = f'h{pod}{switch_id}{host_id}'
                    host_ip   = f'10.{pod}.{switch_id}.{host_id+2}'
                    host      = self.addHost(host_name, ip = host_ip)
                    # create links between edge switch and host
                    self.addLink(host, switch_edge)
                    # add ronte rules for edge switches
                    # mask_down = 0xffffffff
                    # mask_up   = 0x000000ff
                    mask_down = '255.255.255.255'
                    mask_up   = '0.0.0.255'
                    out_port_down = host_id + 1
                    out_port_up   = host_id + 1 + (k // 2)
                    route = {
                        "prefix"   : host_ip,
                        "mask"     : mask_down,
                        "priority" : priority_down,
                        "output"   : out_port_down
                    }
                    suffix_route = {
                        "suffix"   : host_ip,
                        "mask"     : mask_up, 
                        "priority" : priority_up, 
                        "output"   : out_port_up
                    }
                    routing_table[switch_name]["routes"].append(route)
                    routing_table[switch_name]["suffix_routes"].append(suffix_route)
                    swconfig.write(f'sh ovs-ofctl add-flow {switch_name} "priority={priority_down}, ip,nw_dst={host_ip}/{mask_down}, actions=output:{out_port_down}"\n')
                    swconfig.write(f'sh ovs-ofctl add-flow {switch_name} "priority={priority_up  }, ip,nw_dst={host_ip}/{mask_up  }, actions=output:{out_port_up  }"\n')
                
            # create aggr switches with links
            for i in range(k//2): 
                # create aggr switch
                switch_num  = (k // 2) + i
                switch_id   = i
                switch_dpid = f'0000000000{pod:02x}{switch_num:02x}01'
                switch_name = f'agSw{pod}{switch_id}'
                dpid_switch[switch_dpid] = switch_name
                switch_aggr = self.addSwitch(switch_name, 
                                            dpid = switch_dpid)
                pod_switches_aggr.append(switch_aggr)
                # create links between aggr switch and edge switch
                for switch_edge in pod_switches_edge:
                    self.addLink(switch_aggr, switch_edge)
                # add ronte rules for aggr switches
                routing_table[switch_name] = { # initial routing table
                    "routes": [], 
                    "suffix_routes": []
                }
                swconfig.write(f'sh ovs-vsctl set bridge {switch_name} datapath_type=netdev\n')
                for host_id in range (k // 2):
                    host_ip = f'10.{pod}.{host_id}.0'
                    # mask_down = 0xffffff00
                    # mask_up   = 0x0000ff00
                    mask_down = '255.255.255.0'
                    mask_up   = '0.0.255.0'
                    out_port_down = host_id + 1
                    out_port_up   = host_id + 1 + (k // 2)
                    route = {
                        "prefix"   : host_ip,
                        "mask"     : mask_down,
                        "priority" : priority_down,
                        "output"   : host_id + 1
                    }
                    suffix_route = {
                        "suffix"   : host_ip,
                        "mask"     : mask_up, 
                        "priority" : priority_up, 
                        "output"   : host_id + 1 + (k // 2)
                    }
                    routing_table[switch_name]["routes"].append(route)
                    routing_table[switch_name]["suffix_routes"].append(suffix_route)
                    swconfig.write(f'sh ovs-ofctl add-flow {switch_name} "priority={priority_down}, ip,nw_dst={host_ip}/{mask_down}, actions=output:{out_port_down}"\n')
                    swconfig.write(f'sh ovs-ofctl add-flow {switch_name} "priority={priority_up  }, ip,nw_dst={host_ip}/{mask_up  }, actions=output:{out_port_up  }"\n')
            switches_aggr.append(pod_switches_aggr)

        # create core switches and links
        # create core switches
        for j in range(k//2):
            for i in range(k//2):
                switch_id   = (j*(k//2))+i
                switch_dpid = f'0000000000{k:02x}{j:02x}{i:02x}'
                switch_name = f'crSw{switch_id}'
                dpid_switch[switch_dpid] = switch_name
                switch_core = self.addSwitch(switch_name, 
                                            dpid = switch_dpid)
                # create links between core switch and aggr switch
                for num  in range(k):
                    self.addLink(switches_aggr[num][j], switch_core) 
                # add ronte rules for core switches
                routing_table[switch_name] = { # initial routing table
                    "routes": []
                }
                swconfig.write(f'sh ovs-vsctl set bridge {switch_name} datapath_type=netdev\n')
                for pod in range(k):
                    host_ip   = f'10.{pod}.0.0'
                    # mask_down = 0xffff0000
                    mask_down = '255.255.0.0'
                    out_port_down = pod + 1
                    route = {
                        "prefix"   : host_ip,
                        "mask"     : mask_down,
                        "priority" : priority_down,
                        "output"   : out_port_down
                    }
                    routing_table[switch_name]["routes"].append(route)
                    swconfig.write(f'sh ovs-ofctl add-flow {switch_name} "priority={priority_down}, ip,nw_dst={host_ip}/{mask_down}, actions=output:{out_port_down}"\n')

        with open('routing_table.json', 'w') as f:
            json.dump(routing_table, f, indent=4)
        with open('dpid_switch_table.json', 'w') as f:
            json.dump(dpid_switch, f , indent=4)

def main(k, ryu):

    topo = fat_tree_topo()

    if ryu == 2:
        net = Mininet(topo = topo,
                      link = TCLink,
                      controller = RemoteController,
                      switch = OVSSwitch)
    else:
        net = Mininet(topo = topo, 
                      link = TCLink, 
                      controller = RemoteController, 
                      autoSetMacs = True, 
                      autoStaticArp = True)

    net.addController('Ctl0', controller = RemoteController, 
                                      ip = '127.0.0.1', 
                                    port = 6633,
                               protocols = "OpenFlow13")

    # net.build()

    ip_mac_table = {}
    for host in net.hosts:
        ip_mac_table[host.IP()] = host.MAC()
    
    with open('ip_mac_table.json', 'w') as f:
        json.dump(ip_mac_table, f,indent=4)

    net.start()

    if ryu:
        configure_switches(net, k)
        CLI(net)
    else:
        CLI(net, script = 'swconfig')
        CLI(net)

    net.stop()

def configure_switches(net, k):
    info('*** Configuring switches...\n')
    num_switches = len(net.switches)
    
    for switch in net.switches:
        switch_name = switch.name
        info(f'*** Configuring {switch_name}\n')
        set_br = f'ovs-vsctl set bridge {switch_name} datapath_type=netdev'
        switch.cmd(set_br)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--k",   type=int, default=4, help="k order of fat-tree topo")
    parser.add_argument("--ryu", type=int, default=0, help="0 for not using ryu; 1 for using ryu but auto arp setting; 2 for using ryu with all control")
    args = parser.parse_args()
    k = args.k
    ryu = args.ryu
    setLogLevel('info')
    main(k, ryu)