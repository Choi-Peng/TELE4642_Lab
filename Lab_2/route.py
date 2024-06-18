'''
Code Author: Peng, Caikun
File Name: route.py
Create Date: 17/06/2024 
Last Edit Date: 17/06/2024
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
from ryu.lib.packet import arp
import json

def load_routing_table():
    with open('routing_table.json', 'r') as file: 
        file_content = file.read()
        route = json.loads(file_content)
        return route

class MultiSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MultiSwitch13, self).__init__(*args, **kwargs)
        # initialize mac address table.
        self.mac_to_port   = {}
        self.routing_table = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        # load routing table
        if not self.routing_table:
            self.logger.info('Loading routing table...')
            self.routing_table = load_routing_table()
            self.logger.info(self.routing_table)

        datapath = ev.msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        dpid     = datapath.id
        dpid     = f'{dpid:016x}'
        self.logger.info(f'\nSwitch DPID: {dpid}')

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        if dpid in self.routing_table:
            self.logger.info(f"Configuring routes for switch {dpid}")

            # 添加静态路由
            for route in self.routing_table[dpid]['routes']:
                self.logger.info(f"Configuring route for switch {dpid}")
                self.add_route(datapath, 
                               route['prefix'], 
                               route['mask'], 
                               route['priority'], 
                               route['output'])
            if 'suffix_routes' in self.routing_table[dpid]:
                for route in self.routing_table[dpid]['suffix_routes']:
                    self.logger.info(f"Configuring suffix route for switch {dpid}")
                    self.add_suffix_routes(datapath, 
                                route['suffix'], 
                                route['mask'], 
                                route['priority'], 
                                route['output'])

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
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        eth_type = eth_pkt.ethertype
        dst = eth_pkt.dst
        src = eth_pkt.src

        # get the received port number from packet_in message.
        in_port = msg.match['in_port']

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if eth_type != 0x86dd: # IPv6
            self.logger.info(f'\npacket in from dpid={dpid:06x} in_port={in_port}')
            self.logger.info(f'eth_type={eth_type:04x} src={src} dst={dst}')

        if eth_type == 0x0806: # ARP
            self.logger.info('ARP packet')
            arp_pkt     = pkt.get_protocol(arp.arp)
            arp_src_mac = arp_pkt.src_mac
            arp_dst_mac = arp_pkt.dst_mac
            arp_src_ip  = arp_pkt.src_ip
            arp_dst_ip  = arp_pkt.dst_ip
            arp_opcode  = arp_pkt.opcode
            if arp_opcode == 1:
                self.logger.info(f'ARP_REQUEST')
            if arp_opcode == 2:
                self.logger.info(f'ARP_ECHO')
            self.logger.info(f'src_mac={arp_src_mac}, src_ip={arp_src_ip}\n' +
                             f'dst_mac={arp_dst_mac}, dst_ip={arp_dst_ip}')
            
            # if the destination mac address is already learned,
            # decide which port to output the packet, otherwise FLOOD.
            if arp_dst_mac in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
            else:
                out_port = ofproto.OFPP_FLOOD
            self.logger.info(f'out_port={out_port}')
            # construct action list.
            actions = [parser.OFPActionOutput(out_port)]

            # install a flow to avoid packet_in next time.
            if out_port != ofproto.OFPP_FLOOD:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
                self.add_flow(datapath, 1, match, actions)

            # construct packet_out message and send it.
            out = parser.OFPPacketOut(datapath=datapath,
                                    buffer_id=ofproto.OFP_NO_BUFFER,
                                    in_port=in_port, actions=actions,
                                    data=msg.data)
            datapath.send_msg(out)
            self.logger.info(out)
