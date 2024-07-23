'''
Code Author: Peng, Caikun
File Name: ncm_api.py
Create Date: 20/07/2024 
Edited Date: 20/07/2024
Description: REST API for switch configuration, 
    get more information in project wiki:
    https://github.com/Caikun-Peng/TELE4642_Lab/wiki/REST-API-Documentation
Dependencies: json, ryu, subprocess
'''

import logging
import json
import subprocess
import os
import ast

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller import dpset
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication
from ryu.lib import dpid as dpid_lib
from ryu.lib import ofctl_v1_3
from ryu.topology.api import get_switch, get_link, get_host

LOG = logging.getLogger('ncm_api')

def stats_method(method):
    def wrapper(self, req, dpid, *args, **kwargs):
        # Get datapath instance from DPSet
        try:
            dp = self.dpset.get(int(str(dpid), 0))
        except ValueError:
            LOG.exception('Invalid dpid: %s', dpid)
            return Response(status=400)
        if dp is None:
            LOG.error('No such Datapath: %s', dpid)
            return Response(status=404)

        # Get lib/ofctl_* module
        ofctl = ofctl_v1_3

        # Invoke StatsController method
        try:
            ret = method(self, req, dp, ofctl, *args, **kwargs)
            if isinstance(ret, Response):
                return ret
            return Response(content_type='application/json',
                            body=json.dumps(ret))
        except ValueError:
            LOG.exception('Invalid syntax: %s', req.body)
            return Response(status=400)
        except AttributeError:
            LOG.exception('Unsupported OF request in this version: %s',
                          dp.ofproto.OFP_VERSION)
            return Response(status=501)

    return wrapper

class ncmController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(ncmController, self).__init__(req, link, data, **config)
        self.ncm_api_app = data['ncm_api_app']
        self.dpset = data['dpset']
        self.waiters = data['waiters']

    # region topo 
    urlTopo = '/topo'
    ## list dpid
    @route('topo', urlTopo + '/dpid', methods=['GET'])
    def getDpids(self, req, **kwargs):
        body = self.get_dipds(req, **kwargs)
        return Response(content_type='application/json', body=body)

    def get_dipds(self, req, **kwargs):
        dps = list(self.dpset.dps.keys())
        body = json.dumps(dps)
        return body

    ## switches
    urlTopoSwitches = urlTopo + '/switches'
    @route('topo', urlTopoSwitches, methods=['GET'])
    def listSwitches(self, req, **kwargs):
        body = self.getSwitch(req, **kwargs) 
        return body

    urlTopoSwitch = urlTopoSwitches + '/{dpid}'
    @route('topo', urlTopoSwitch, methods=['GET'])
    def listSwitch(self, req, **kwargs):
        body = self.getSwitch(req, **kwargs) 
        return body

    def getSwitch(self, req, **kwargs):
        dpid = None
        if 'dpid' in kwargs:
            kwargs['dpid'] = parse_dpid(kwargs['dpid'])
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        switches = get_switch(self.ncm_api_app, dpid)
        body = json.dumps([switch.to_dict() for switch in switches])
        return Response(content_type='application/json', body=body)

    ## hosts
    urlTopoHosts = urlTopo + '/hosts' 
    @route('topo', urlTopoHosts, methods=['GET'])
    def listHosts(self, req, **kwargs):
        body = self.getHost(req, **kwargs)
        return body

    urlTopoHost = urlTopoHosts + '/{dpid}'
    @route('topo', urlTopoHost, methods=['GET'])
    def listHost(self, req, **kwargs):
        body = self.getHost(req, **kwargs)
        return body

    def getHost(self, req, **kwargs):
        dpid = None
        if 'dpid' in kwargs:
            kwargs['dpid'] = parse_dpid(kwargs['dpid'])
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        hosts = get_host(self.ncm_api_app, dpid)
        body = json.dumps([host.to_dict() for host in hosts])
        return Response(content_type='application/json', body=body)

    ## links (not realized yet)
    urlTopoLinks = urlTopo + '/links'
    @route('topo', urlTopoLinks, methods=['GET'])
    def listLinks(self, req, **kwargs):
        body = self.getLink(req, **kwargs)
        return body

    urlTopoLink = urlTopoLinks + '/{dpid}'
    @route('topo', urlTopoLink, methods=['GET'])
    def listLink(self, req, **kwargs):
        body = self.getLink(req, **kwargs)
        return body

    # urlTopoLinkPort = urlTopoLink + '/{portNum}'

    def getLink(self, req, **kwargs):
        try: 
            dpid = None
            if 'dpid' in kwargs:
                kwargs['dpid'] = parse_dpid(kwargs['dpid'])
                dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
            links = get_link(self.ncm_api_app, dpid)
            body = json.dumps([link.to_dict() for link in links])
            return Response(content_type='application/json', body=body)
        except Exception as e:
            body = json.dumps({'status': 'failure', 'reason': str(e)})
            return Response(content_type='application/json', body=body)


    # endregion
    
    # region rate
    urlRate = '/rate'
    ## switches
    urlRateSwitches = urlRate + '/switches'
    @route('rate', urlRateSwitches, methods=['GET'])
    def listRates(self, req, **kwargs):
        body = self.getRate(req, **kwargs)
        return body
    
    @route('rate', urlRateSwitches, methods=['PUT'])
    def setRates(self, req, **kwargs):
        print('putting rates')
        body = self.putRate(req, **kwargs)
        return body

    urlRateSwitch = urlRateSwitches + '/{dpid}'
    @route('rate', urlRateSwitch, methods=['GET'])
    def listRate(self, req, **kwargs):
        body = self.getRate(req, **kwargs)
        return body

    @route('rate', urlRateSwitch, methods=['PUT'])
    def setRate(self, req, **kwargs):
        body = self.putRate(req, **kwargs)
        return body

    urlRateSwitchPort = urlRateSwitch + '/{portNum}'
    @route('rate', urlRateSwitchPort, methods=['GET'])
    def listRatePort(self, req, **kwargs):
        body = self.getRate(req, **kwargs)
        return body

    @route('rate', urlRateSwitchPort, methods=['PUT'])
    def setRatePort(self, req, **kwargs):
        body = self.putRate(req, **kwargs)
        return body

    def getRate(self, req, **kwargs):
        try:
            dpid = None
            if 'dpid' in kwargs:
                dpid = parse_dpid(kwargs['dpid'])
                dpid = dpid_lib.str_to_dpid(dpid)
            switches = get_switch(self.ncm_api_app, dpid)
            switchesTemp = json.dumps([switch.to_dict() for switch in switches])
            # print(f'switchesTemp: {switchesTemp}')
            dpids = self.get_dpid(switchesTemp)
            # print(f'dpids_initial: {dpids}')

            portRate = []
            for dpid in dpids:
                portRate.append({"dpid": dpid})
                portNum = None
                if 'portNum' in kwargs:
                    portNum = parse_portNum(kwargs['portNum'])
                port_name = self.get_port_names(switchesTemp, [dpid], portNum)
                # print(f'port_name: {port_name}')

                port_info = []
                for portName in port_name:
                    # print(f'portName:{portName}')
                    cmd = f'ovs-vsctl list interface {portName}'
                    process = subprocess.run(cmd.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    output = process.stdout

                    ingress_policing_burst = None
                    ingress_policing_rate = None

                    for line in output.splitlines():
                        if 'ingress_policing_burst' in line:
                            ingress_policing_burst = line.split(":")[-1].strip()
                        elif 'ingress_policing_rate' in line:
                            ingress_policing_rate = line.split(":")[-1].strip()

                    port_info.append({
                        'port_name': portName,
                        'ingress_policing_burst': ingress_policing_burst,
                        'ingress_policing_rate': ingress_policing_rate
                    })

                portRate.append({"ports":port_info})

            body = json.dumps(portRate)
            return Response(content_type='application/json', body=body)

        except subprocess.CalledProcessError as e:
            body = json.dumps({'status': 'failure', 'reason': str(e)})
            return Response(content_type='application/json', body=body)

    def putRate(self, req, **kwargs):
        try:
            dpid = None
            if 'dpid' in kwargs:
                dpid = parse_dpid(kwargs['dpid'])
                dpid = dpid_lib.str_to_dpid(dpid)
            switches = get_switch(self.ncm_api_app, dpid)
            switchesTemp = json.dumps([switch.to_dict() for switch in switches])
            # print(f'switchesTemp: {switchesTemp}')
            dpids = self.get_dpid(switchesTemp)
            # print(f'dpids_initial: {dpids}')

            rate_limit = json.loads(req.body)
            rate = rate_limit.get('rate', None)
            burst = rate_limit.get('burst', None)

            if rate is not None and burst is not None:
                for dpid in dpids:
                    portNum = None
                    if 'portNum' in kwargs:
                        portNum = parse_portNum(kwargs['portNum'])
                    port_name = self.get_port_names(switchesTemp, dpid, portNum)
                    # print(f'port_name: {port_name}')

                    body = []
                    for portName in port_name:
                        command = f'ovs-vsctl set interface {portName} ingress_policing_rate={rate}'
                        os.system(command)
                        command = f'ovs-vsctl set interface {portName} ingress_policing_burst={burst}'
                        os.system(command)
                        info = f'Set switch {dpid} port {portName} rate to {rate} kbps and burst to {burst} kbps'
                        print(info)
                        body.append(info)
                    
                    body = json.dumps(body)
                
                return Response(content_type='application/json', body=body)
            else:
                body = json.dumps({'status': 'failure', 'reason': 'Invalid rate or burst value'})
                return Response(content_type='application/json', body=body)
        except Exception as e:
            body = json.dumps({'status': 'failure', 'reason': str(e)})
            return Response(content_type='application/json', body=body)

    # endregion

    # region flow
    urlFlow = '/flow'
    ## switches
    urlFlowSwitches = urlFlow + '/switches'
    @route('flow', urlFlowSwitches, methods=['GET'])
    def listFlows(self, reg, **kwargs):
        dpids = json.loads(self.get_dipds(reg, **kwargs))
        # print(dpids, len(dpids), type(dpids))
        flows = {}
        for dpid in dpids:
            # print(dpid)
            kwargs['dpid'] = dpid
            # print(kwargs)
            flow = self.getFlow(reg, **kwargs)
            flow = json.loads(flow.body)
            flows[str(dpid)] = flow[str(dpid)]
        body = Response(content_type='application/json', body=json.dumps(flows))
        return body
    
    @route('flow', urlFlowSwitches, methods=['PUT'])
    def setFlows(self, reg, **kwargs):
        body = self.putFlow(reg, **kwargs)
        return body

    @route('flow', urlFlowSwitches, methods=['DELETE'])
    def delFlows(self, reg, **kwargs):
        body = self.deleteFlow(reg, **kwargs)
        return body

    urlFlowSwitch = urlFlowSwitches + '/{dpid}'
    @route('flow', urlFlowSwitch, methods=['GET'])
    def listFlow(self, reg, **kwargs):
        # print('listFlow')
        body = self.getFlow(reg, **kwargs)
        return body

    @route('flow', urlFlowSwitch, methods=['PUT'])
    def setFlow(self, reg, **kwargs):
        body = self.putFlow(reg, **kwargs)
        return body

    @route('flow', urlFlowSwitch, methods=['DELETE'])
    def delFlow(self, reg, **kwargs):
        body = self.deleteFlow(reg, **kwargs)
        return body

    urlFlowSwitchTable = urlFlowSwitch + '/{tableNum}'
    @route('flow', urlFlowSwitchTable, methods=['GET'])
    def listFlowTable(self, reg, **kwargs):
        body = self.getFlow(reg, **kwargs)
        return body

    @route('flow', urlFlowSwitchTable, methods=['PUT'])
    def setFlowTable(self, reg, **kwargs):
        body = self.putFlow(reg, **kwargs)
        return body

    @route('flow', urlFlowSwitchTable, methods=['DELETE'])
    def delFlowTable(self, reg, **kwargs):
        body = self.deleteFlow(reg, **kwargs)
        return body

    @stats_method
    def getFlow(self, req, dp, ofctl, **kwargs):
        try:
            flow = req.json if req.body else {}
            # print(f'get flow: {flow}')
            flow_stats = ofctl.get_flow_stats(dp, self.waiters, flow)
            for dpid in flow_stats:
                # print(flow_stats[dpid])
                formatted_flows = {dpid: []}
                for flow in flow_stats[dpid]:
                    if 'tableNum' in kwargs:
                        if int(kwargs['tableNum']) == int(flow.get('table_id')):
                            formatted_flow = {
                                "priority": flow.get('priority'),
                                "cookie": flow.get('cookie'),
                                "idle_timeout": flow.get('idle_timeout'),
                                "hard_timeout": flow.get('hard_timeout'),
                                "actions": [action for action in flow.get('actions', [])],
                                "match": {k: v for k, v in flow.get('match', {}).items()},
                                "byte_count": flow.get('byte_count'),
                                "duration_sec": flow.get('duration_sec'),
                                "duration_nsec": flow.get('duration_nsec'),
                                "packet_count": flow.get('packet_count'),
                                "table_id": flow.get('table_id')
                            }    
                    else:
                        formatted_flow = {
                            "priority": flow.get('priority'),
                            "cookie": flow.get('cookie'),
                            "idle_timeout": flow.get('idle_timeout'),
                            "hard_timeout": flow.get('hard_timeout'),
                            "actions": [action for action in flow.get('actions', [])],
                            "match": {k: v for k, v in flow.get('match', {}).items()},
                            "byte_count": flow.get('byte_count'),
                            "duration_sec": flow.get('duration_sec'),
                            "duration_nsec": flow.get('duration_nsec'),
                            "packet_count": flow.get('packet_count'),
                            "table_id": flow.get('table_id')
                        }
                formatted_flows[dpid].append(formatted_flow)

            return formatted_flows

        except Exception as e:
            error_message = {'status': 'failure', 'reason': str(e)}
            return Response(content_type='application/json', body=json.dumps(error_message), status=500)

    def setFlow(self, reg, **kwargs):
        try:
            body
            return Response(content_type='application/json', body=body)
        except Exception as e:
            body = json.dumps({'status': 'failure', 'reason': str(e)})
            return Response(content_type='application/json', body=body, status=500)

    def deleteFlow(self, reg, **kwargs):
        try:
            body
            return Response(content_type='application/json', body=body)
        except Exception as e:
            body = json.dumps({'status': 'failure', 'reason': str(e)})
            return Response(content_type='application/json', body=body, status=500)

    # endregion

    # region functions
    def get_dpid(self, switches):
        switches = json.loads(switches)
        dpid = []
        for switch in switches:
            # print(f'get_dpid.switch: {switch}')
            dpid.append(switch['dpid'])
        return dpid

    def get_port_names(self, switches, dpid, port_no=None):
        switches = json.loads(switches)
        # print(f'get_port_names.switches: {switches}')
        # print(f'get_port_names.dpid_initial: {dpid}')
        dpids = [parse_dpid(dpid)]
        # print(f'get_port_names.dpids: {dpids}')
        for dpid in dpids:
            # print(f'get_port_names.dpid: {dpid}')
            for switch in switches:
                if switch["dpid"] == dpid:
                    if port_no is None:
                        return [port["name"] for port in switch["ports"]]
                    else:
                        port_no = parse_portNum(port_no)
                        for port in switch["ports"]:
                            if port["port_no"] == port_no:
                                return [port["name"]]
        return None
    # endregion

def parse_dpid(dpid_str):
    # print(f'parse_dpid.dpid_str: {dpid_str}')
    # print(type(dpid_str))
    try:
        if isinstance(dpid_str, list):
            for dpid in dpid_str:
                if int(dpid[0]):
                    dpid = int(dpid)
                    # print(f"converte to 0x: {dpid}")
                    return f"{dpid:016x}"
                else: 
                    return dpid
        elif isinstance(dpid_str, str):
            if int(dpid_str[0]):
                dpid_str = int(dpid_str)
                # print(f"converte to 0x: {dpid_str}")
                return f"{dpid_str:016x}"
            else: 
                return dpid_str
        elif isinstance(dpid_str, int):
            if str(dpid_str)[0]:
                # print(f"converte to 0x: {dpid_str}")
                return f"{dpid_str:016x}"
            else: 
                return dpid_str
    except ValueError:
        return dpid_str

def parse_portNum(portNum_str):
    # print(f'parse_portNum.portNum_str: {portNum_str}')
    try:
        portNum = int(portNum_str)
        return f"{portNum:08x}"
    except ValueError:
        return portNum_str

class ncmAPI(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(ncmAPI, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.waiters = {}
        
        wsgi = kwargs['wsgi']

        data = {
            'ncm_api_app': self,
            'dpset': self.dpset,
            'waiters': self.waiters
        }

        wsgi.register(ncmController, data)

    @set_ev_cls([ofp_event.EventOFPFlowStatsReply,], MAIN_DISPATCHER)
    def stats_reply_handler(self, ev):
        # print('stats_reply_handler')
        msg = ev.msg
        dp = msg.datapath

        if dp.id not in self.waiters:
            return
        if msg.xid not in self.waiters[dp.id]:
            return
        lock, msgs = self.waiters[dp.id][msg.xid]
        msgs.append(msg)

        flags = 0
        if dp.ofproto.OFP_VERSION >= ofproto_v1_3.OFP_VERSION:
            flags = dp.ofproto.OFPMPF_REPLY_MORE

        if msg.flags & flags:
            return
        del self.waiters[dp.id][msg.xid]
        lock.set()

    @set_ev_cls([ofp_event.EventOFPSwitchFeatures,
                 ofp_event.EventOFPQueueGetConfigReply,
                 ofp_event.EventOFPRoleReply,
                 ], MAIN_DISPATCHER)
    def features_reply_handler(self, ev):
        print('features_reply_handler')
        msg = ev.msg
        dp = msg.datapath

        if dp.id not in self.waiters:
            return
        if msg.xid not in self.waiters[dp.id]:
            return
        lock, msgs = self.waiters[dp.id][msg.xid]
        msgs.append(msg)

        del self.waiters[dp.id][msg.xid]
        lock.set()
