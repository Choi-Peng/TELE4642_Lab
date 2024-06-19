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
        self.ip_to_port    = {}
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
            # self.logger.info(self.routing_table)
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
            if switch_name not in self.ip_to_port:
                self.ip_to_port.setdefault(switch_name, [])
            if switch_name not in self.route_check:
                self.route_check.setdefault(switch_name, [])

            # 添加静态路由
            self.logger.info(f"Configuring route for switch {switch_name}")
            for route in self.routing_table[switch_name]['routes']:
                # ip_to_port_data = {}
                self.add_route(datapath, 
                               route['prefix'], 
                               route['mask'], 
                               route['priority'], 
                               route['output'])
                self.route_check[switch_name].append(route)
                # ip_to_port_data[route['prefix']] = route['output']
                # self.ip_to_port[switch_name].append(ip_to_port_data)
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
                # # using routing table to get out port
                # for route in self.route_check[switch_name]:
                #     self.logger.info(f'get route rule: {route}')
                #     try :
                #         ip_indicator = self.apply_mask(route['prefix'], route['mask'])
                #     except Exception as e:
                #         ip_indicator = self.apply_mask(route['suffix'], route['mask'])
                #     ip_detected  = self.apply_mask(arp_dst_ip, route['mask'])
                #     if ip_detected == ip_indicator:
                #         out_port = route['output']
                #         self.logger.info(f'Get out_port from table: {out_port}')
                #         break
                #     else:
                #         out_port = ofproto.OFPP_FLOOD
                #         self.logger.info(f'Initial out_port={out_port}')
                #             # install a flow to avoid packet_in next time.
                # if arp_dst_mac == '00:00:00:00:00:00':
                #     arp_dst_mac = self.ip_mac_table.get(arp_dst_ip)
                if dst in self.mac_to_port[switch_name]:
                    out_port = self.mac_to_port[switch_name][dst]
                # if dst_ip in self.ip_to_port[switch_name]:
                #     out_port = self.ip_to_port[switch_name][dst_ip]
                    print(f'out_port={out_port}')                            
                else:
                    out_port = ofproto.OFPP_FLOOD
                    print(f'out_port={out_port}')                
                if out_port != ofproto.OFPP_FLOOD:
                    actions = [parser.OFPActionOutput(out_port)]
                    match = parser.OFPMatch(in_port=in_port, eth_dst=arp_dst_mac)
                    self.add_flow(datapath, 300, match, actions)
                self.handle_arp(datapath, out_port, arp_pkt)
                    # self.send_arp_reply(datapath, out_port, arp_dst_mac, arp_dst_ip, arp_src_mac, arp_src_ip)

            if arp_opcode == 2:
                self.logger.info(f'ARP_REPLY')


        if eth_pkt.ethertype == 0x0800: # IPv4
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            self.logger.info('IPv4 Packet')
            if ip_pkt.proto == inet.IPPROTO_ICMP:
                icmp_pkt = pkt.get_protocol(icmp.icmp)
                self.logger.info("Received ICMP packet: type=%s, code=%s", icmp_pkt.type, icmp_pkt.code)
                if icmp_pkt and icmp_pkt.type == icmp.ICMP_ECHO_REQUEST:
                    self.reply_to_icmp_echo_request(datapath, msg, eth, ip_pkt, icmp_pkt)
                    self.logger.info('ICMP ECHO')

    def handle_arp(self, datapath, port, arp_pkt):
        src_mac = self.ip_mac_table.get(arp_pkt.src_ip)
        dst_mac = self.ip_mac_table.get(arp_pkt.dst_ip)

        if dst_mac:
            self.send_arp_reply(datapath, port, dst_mac, arp_pkt.dst_ip, src_mac, arp_pkt.src_ip)

    def send_arp_reply(self, datapath, port, src_mac, src_ip, dst_mac, dst_ip):
        # 创建一个包实例
        pkt = packet.Packet()
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 添加以太网头部，注意目标 MAC 是发起 ARP 请求的源 MAC
        eth = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=0x0806)
        pkt.add_protocol(eth)

        # 添加 ARP 回应协议数据
        arp_reply = arp.arp(opcode=arp.ARP_REPLY,
                            src_mac=src_mac, src_ip=src_ip,
                            dst_mac=dst_mac, dst_ip=dst_ip)
        pkt.add_protocol(arp_reply)

        # 序列化整个包，为发送做准备
        pkt.serialize()

        # 定义一个动作，即通过哪个端口发送这个包
        actions = [parser.OFPActionOutput(port)]

        # 创建数据包输出对象
        out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath,
                                                buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                                                in_port=datapath.ofproto.OFPP_CONTROLLER,
                                                actions=actions,
                                                data=pkt.data)
        # 发送数据包
        datapath.send_msg(out)
        self.logger.info(f'ARP_REPLY  out_port={port}, src_mac={src_mac}, src_ip={src_ip}, dst_mac={dst_mac}, dst_ip={dst_ip}')
        # self.logger.info(out)

    def reply_to_icmp_echo_request(self, datapath, msg, eth, ip_pkt, icmp_pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        data = msg.data
        in_port = msg.match['in_port']

        # 创建 ICMP Echo Reply
        e = ethernet.ethernet(dst=eth.src, src=eth.dst, ethertype=eth.ethertype)
        ip = ipv4.ipv4(dst=ip_pkt.src, src=ip_pkt.dst, proto=ip_pkt.proto)
        echo_reply = icmp.icmp(type_=icmp.ICMP_ECHO_REPLY, code=icmp.ICMP_ECHO_REPLY_CODE,
                               csum=0, data=icmp_pkt.data)
        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(ip)
        p.add_protocol(echo_reply)
        p.serialize()

        # 发送数据包
        actions = [parser.OFPActionOutput(ofproto.OFPP_IN_PORT)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=in_port, actions=actions, data=p.data)
        datapath.send_msg(out)

    def apply_mask(self, prefix, mask):
        ip_int = int(ipaddress.IPv4Address(prefix))
        mask_int = int(hex(mask), 16)

        # 进行按位与操作
        network_int = ip_int & mask_int

        # 将结果转换回IP地址格式
        network_ip = str(ipaddress.IPv4Address(network_int))
        return network_ip