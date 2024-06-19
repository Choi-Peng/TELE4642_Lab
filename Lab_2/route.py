'''
Code Author: Peng, Caikun
File Name: route.py
Create Date: 17/06/2024 
Last Edit Date: 19/06/2024
Description: Configure routes for switches
Dependencies: ryu
'''

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import icmp
import json
import ipaddress

def load_json_file(file_name):
    with open(file_name, 'r') as file: 
        file_content = file.read()
        data = json.loads(file_content)
        return data

class MultiSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MultiSwitch13, self).__init__(*args, **kwargs)
        # initialize mac address table.
        self.mac_to_port   = {}
        self.routing_table = {}
        self.route_check   = {}
        self.ip_mac_table  = {}
        self.dpid_switch_table = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        # load routing table
        if not self.routing_table:
            self.logger.info('Loading routing table...')
            self.routing_table = load_json_file('routing_table.json')
        if not self.dpid_switch_table:
            self.dpid_switch_table = load_json_file('dpid_switch_table.json')    

        datapath = ev.msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        dpid     = datapath.id
        dpid     = f'{dpid:016x}'
        switch_name = self.dpid_switch_table.get(dpid)
        self.logger.info(f'\nSwitch DPID: {dpid}, Switch name: {switch_name}')

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        if self.routing_table[switch_name]:
            self.logger.info(f"Configuring routes for switch {switch_name}")
            if switch_name not in self.route_check:
                self.route_check.setdefault(switch_name, [])

            self.logger.info(f"Configuring route for switch {switch_name}")
            for route in self.routing_table[switch_name]['routes']:
                self.add_route(datapath, 
                               route['prefix'], 
                               route['mask'], 
                               route['priority'], 
                               route['output'])
                self.route_check[switch_name].append(route)
            if 'suffix_routes' in self.routing_table[switch_name]:
                self.logger.info(f"Configuring suffix route for switch {switch_name}")
                for route in self.routing_table[switch_name]['suffix_routes']:
                    self.add_suffix_routes(datapath, 
                                route['suffix'], 
                                route['mask'], 
                                route['priority'], 
                                route['output'])
                    self.route_check[switch_name].append(route)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def add_route(self, datapath, ip, mask, priority, port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=(ip, mask))
        actions = [parser.OFPActionOutput(port)]
        self.add_flow(datapath, priority, match, actions)

    def add_suffix_routes(self, datapath, ip, mask, priority, port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=(ip, mask))
        actions = [parser.OFPActionOutput(port)]
        self.add_flow(datapath, priority, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if not self.ip_mac_table:
            self.logger.info('Loading IP-MAC table...')
            self.ip_mac_table = load_json_file('ip_mac_table.json')
            with open('routes.json', 'w') as f:
                json.dump(self.route_check, f, indent=4)

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid        = datapath.id
        switch_name = self.dpid_switch_table.get(f'{dpid:016x}')
        # if switch_name not in self.mac_to_port:
        self.mac_to_port.setdefault(switch_name, {})

        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        eth_type = eth_pkt.ethertype
        dst = eth_pkt.dst
        src = eth_pkt.src

        # get the received port number from packet_in message.
        in_port = msg.match['in_port']

        # learn a mac address to avoid FLOOD next time.
        if src not in self.mac_to_port[switch_name]:
            self.mac_to_port[switch_name][src] = in_port
            with open('mac_to_port.json', 'w') as f:
                json.dump(self.mac_to_port, f, indent=4)

        if eth_type != 0x86dd: # IPv6
            self.logger.info(f'\npacket in from switch {switch_name} in_port={in_port}')
            self.logger.info(f'eth_type={eth_type:04x} src={src} dst={dst}')

        if eth_type == 0x0806: # ARP
            self.logger.info('ARP packet')
            arp_pkt     = pkt.get_protocol(arp.arp)
            arp_src_mac = arp_pkt.src_mac
            arp_dst_mac = arp_pkt.dst_mac
            arp_src_ip  = arp_pkt.src_ip
            arp_dst_ip  = arp_pkt.dst_ip
            arp_opcode  = arp_pkt.opcode
            self.logger.info(f'src_mac={arp_src_mac}, src_ip={arp_src_ip}\n' +
                             f'dst_mac={arp_dst_mac}, dst_ip={arp_dst_ip}')
            if arp_opcode == 1:
                self.logger.info(f'ARP_REQUEST')
                # using routing table to get out port
                if dst in self.mac_to_port[switch_name]:
                    out_port = self.mac_to_port[switch_name][dst]
                    print(f'out_port={out_port}')                            
                else:
                    out_port = ofproto.OFPP_FLOOD
                    print(f'out_port={out_port}')                
                if out_port != ofproto.OFPP_FLOOD:
                    actions = [parser.OFPActionOutput(out_port)]
                    match = parser.OFPMatch(in_port=in_port, eth_dst=arp_dst_mac)
                    self.add_flow(datapath, 1, match, actions)
                self.handle_arp(datapath, out_port, arp_pkt)

            if arp_opcode == 2:
                self.logger.info(f'ARP_REPLY')

    def handle_arp(self, datapath, port, arp_pkt):
        src_mac = self.ip_mac_table.get(arp_pkt.src_ip)
        dst_mac = self.ip_mac_table.get(arp_pkt.dst_ip)

        if dst_mac:
            self.send_arp_reply(datapath, port, dst_mac, arp_pkt.dst_ip, src_mac, arp_pkt.src_ip)

    def send_arp_reply(self, datapath, port, src_mac, src_ip, dst_mac, dst_ip):
        pkt = packet.Packet()
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        eth = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=0x0806)
        pkt.add_protocol(eth)

        arp_reply = arp.arp(opcode=arp.ARP_REPLY,
                            src_mac=src_mac, src_ip=src_ip,
                            dst_mac=dst_mac, dst_ip=dst_ip)
        pkt.add_protocol(arp_reply)

        pkt.serialize()

        actions = [parser.OFPActionOutput(port)]

        out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath,
                                                buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                                                in_port=datapath.ofproto.OFPP_CONTROLLER,
                                                actions=actions,
                                                data=pkt.data)
        datapath.send_msg(out)
        self.logger.info(f'ARP_REPLY  out_port={port}, src_mac={src_mac}, src_ip={src_ip}, dst_mac={dst_mac}, dst_ip={dst_ip}')

    def apply_mask(self, prefix, mask):
        ip_int = int(ipaddress.IPv4Address(prefix))
        mask_int = int(hex(mask), 16)

        network_int = ip_int & mask_int

        network_ip = str(ipaddress.IPv4Address(network_int))
        return network_ip