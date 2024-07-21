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

import json
import subprocess
import os

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
# from ryu.app.ofctl_rest import StatsController as rest
from ryu.app.ofctl_rest import StatsController
from ryu.lib import dpid as dpid_lib
from ryu.lib import ofctl_v1_3 as ofctl
from ryu.topology.api import get_switch, get_link, get_host

class ncmController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(ncmController, self).__init__(req, link, data, **config)
        self.ncm_api_app = data['ncm_api_app']
        self.dpset = data['dpset']
        self.waiters = data['waiters']
        self.link = link
        print(f'link: {link}')
        print(f'data: {data}')

    # region topo 
    urlTopo = '/topo'

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

    # # region flow
    # urlFlow = '/flow'
    # ## switches
    # urlFlowSwitches = urlFlow + '/switches'
    # @route('flow', urlFlowSwitches, methods=['GET'])
    # def listFlows(self, reg, **kwargs):
    #     body = self.getFlow(reg, **kwargs)
    #     return body
    
    # @route('flow', urlFlowSwitches, methods=['PUT'])
    # def setFlows(self, reg, **kwargs):
    #     body = self.putFlow(reg, **kwargs)
    #     return body

    # @route('flow', urlFlowSwitches, methods=['DELETE'])
    # def delFlows(self, reg, **kwargs):
    #     body = self.deleteFlow(reg, **kwargs)
    #     return body

    # urlFlowSwitch = urlFlowSwitches + '/{dpid}'
    # @route('flow', urlFlowSwitch, methods=['GET'])
    # def listFlow(self, reg, **kwargs):
    #     # return ofctl.get_flow_stats(dp, self.waiters, {})
    #     body = self.getFlow(reg, **kwargs)
    #     return body

    # @route('flow', urlFlowSwitch, methods=['GET'])
    # def listFlow(self, req, **kwargs):
    #     try:
    #         dpid = None
    #         if 'dpid' in kwargs:
    #             dpid = parse_dpid(kwargs['dpid'])
    #             dpid = dpid_lib.str_to_dpid(dpid)
    #             print(f'dpid: {dpid}')
    #         dp = self.dpset.get(dpid)
    #         print(f'dp: {dp}')
    #         if dp is None:
    #             return Response(status=404, body=json.dumps({'error': 'datapath not found'}))

    #         print(f'ofctl: {ofctl}')
    #         flow_stats = StatsController.get_flow_stats_api(req, dp, ofctl, {})
    #         print(f'flow_stats: {flow_stats}')
    #         return Response(content_type='application/json', body=json.dumps(flow_stats))


    #         controller_instance = StatsController(data={'dpset': app.dpset, 'waiters': app.waiters})
    #         print(f'controller_instance: {controller_instance}')

    #         class DummyRequest:
    #             body = ''
    #             json = {}

    #         req = DummyRequest()
    
    #         # Using the ofctl library to get flow stats
    #         print(f'ofctl: {ofctl}')
    #         flow_stats = controller_instance.get_flow_stats_api(req, dp, ofctl, {})
    #         print(f'flow_stats: {flow_stats}')
    #         return Response(content_type='application/json', body=json.dumps(flow_stats))

    #     except Exception as e:
    #         return Response(content_type='application/json', body=json.dumps({'error': str(e)}), status=500)
    
    # # def fetch_flow_stats(dpid):
    # #     # You must obtain an instance of datapath (dp) using dpid
    # #     dp = self.dpset.get(dpid)
    # #     if not dp:
    # #         raise ValueError("No such datapath")

    # #     # Instantiate the controller with appropriate data
    # #     controller_instance = StatsController(request=None, link=None, data={'dpset': self.dpset, 'waiters': self.waiters})
        
    # #     # Mimicking a request object if necessary
    # #     class DummyRequest:
    # #         body = ''
    # #         json = {}

    # #     req = DummyRequest()
        
    # #     # Call the method directly - this might need custom handling based on your app's architecture
    # #     response = controller_instance.get_flow_stats_api(req, dp, ofctl_v1_3, {})
    # #     return response        

    # @route('flow', urlFlowSwitch, methods=['PUT'])
    # def setFlow(self, reg, **kwargs):
    #     body = self.putFlow(reg, **kwargs)
    #     return body

    # @route('flow', urlFlowSwitch, methods=['DELETE'])
    # def delFlow(self, reg, **kwargs):
    #     body = self.deleteFlow(reg, **kwargs)
    #     return body

    # urlFlowSwitchTable = urlFlowSwitch + '/{tableNum}'
    # @route('flow', urlFlowSwitchTable, methods=['GET'])
    # def listFlowTable(self, reg, **kwargs):
    #     body = self.getFlow(reg, **kwargs)
    #     return body

    # @route('flow', urlFlowSwitchTable, methods=['PUT'])
    # def setFlowTable(self, reg, **kwargs):
    #     body = self.putFlow(reg, **kwargs)
    #     return body

    # @route('flow', urlFlowSwitchTable, methods=['DELETE'])
    # def delFlowTable(self, reg, **kwargs):
    #     body = self.deleteFlow(reg, **kwargs)
    #     return body

    # # def getFlow(self, reg, **kwargs):
    # #     try: 
    # #         dpid = None
    # #         if 'dpid' in kwargs:
    # #             dpid = parse_dpid(kwargs['dpid'])
    # #             dpid = dpid_lib.str_to_dpid(dpid)
    # #             print(f"Parsed dpid: {dpid}")
    # #         switches = get_switch(self.ncm_api_app, dpid)
    # #         switchesTemp = json.dumps([switch.to_dict() for switch in switches])
    # #         print(f'switchesTemp: {switchesTemp}')
    # #         dpids = self.get_dpid(switchesTemp)
    # #         print(f'dpids_initial: {dpids}')

    # #         for dpid in dpids:
    # #             print(f'dpid: {dpid}')
    # #             flow_request_body = {'dpid': dpid}
    # #             flow_stats = rest.get_flow_stats(self.ncm_api_app, flow_request_body, 'flow')
    # #             print(f'dpid: {dpid}')

    # #             formatted_flows = {}
    # #             for flow in flow_stats:
    # #                 flow_dpid = flow['dpid']
    # #                 if flow_dpid not in formatted_flows:
    # #                     formatted_flows[flow_dpid] = []
    # #                 flow_entry = {
    # #                     "priority": flow.get('priority'),
    # #                     "cookie": flow.get('cookie'),
    # #                     "idle_timeout": flow.get('idle_timeout'),
    # #                     "hard_timeout": flow.get('hard_timeout'),
    # #                     "actions": [action for action in flow.get('actions', [])],
    # #                     "match": {k: v for k, v in flow.get('match', {}).items()},
    # #                     "byte_count": flow.get('byte_count'),
    # #                     "duration_sec": flow.get('duration_sec'),
    # #                     "duration_nsec": flow.get('duration_nsec'),
    # #                     "packet_count": flow.get('packet_count'),
    # #                     "table_id": flow.get('table_id')
    # #                 }
    # #                 formatted_flows[flow_dpid].append(flow_entry)
    # #         body = json.dumps(formatted_flows)
    # #         return Response(content_type='application/json', body=json.dumps(formatted_flows))
    # #     except Exception as e:
    # #         body = json.dumps({'status': 'failure', 'reason': str(e)})
    # #         return Response(content_type='application/json', body=body, status=500)

    # def getFlow(self, req, **kwargs):
    #     try:
    #         dpid = None
    #         if 'dpid' in kwargs:
    #             dpid = parse_dpid(kwargs['dpid'])
    #             dpid = dpid_lib.str_to_dpid(dpid)
    #         print(f'dpid: {dpid}')
    #         dp = self.dpset.get(dpid)
    #         print(f'dp: {dp}')

    #         # Fetch flow statistics using ofctl_rest's functionality
    #         stats = StatsController(req, dp, ofctl, **kwargs)
    #         print(stats)
    #         flow_stats = stats.get_flow_stats_api(req, dp, ofctl, **kwargs)
    #         print(f'flow_stats: {flow_stats}')

    #         # Format the flow entries in the desired JSON structure
    #         formatted_flows = {str(dpid): []}
    #         for flow in flow_stats:
    #             formatted_flow = {
    #                 "priority": flow.get('priority'),
    #                 "cookie": flow.get('cookie'),
    #                 "idle_timeout": flow.get('idle_timeout'),
    #                 "hard_timeout": flow.get('hard_timeout'),
    #                 "actions": [action for action in flow.get('actions', [])],
    #                 "match": {k: v for k, v in flow.get('match', {}).items()},
    #                 "byte_count": flow.get('byte_count'),
    #                 "duration_sec": flow.get('duration_sec'),
    #                 "duration_nsec": flow.get('duration_nsec'),
    #                 "packet_count": flow.get('packet_count'),
    #                 "table_id": flow.get('table_id')
    #             }
    #             formatted_flows[str(dpid)].append(formatted_flow)

    #         return Response(content_type='application/json', body=json.dumps(formatted_flows))
    #     except Exception as e:
    #         error_message = {'status': 'failure', 'reason': str(e)}
    #         return Response(content_type='application/json', body=json.dumps(error_message), status=500)


    # def setFlow(self, reg, **kwargs):
    #     try:
    #         body
    #         return Response(content_type='application/json', body=body)
    #     except Exception as e:
    #         body = json.dumps({'status': 'failure', 'reason': str(e)})
    #         return Response(content_type='application/json', body=body, status=500)

    # def deleteFlow(self, reg, **kwargs):
    #     try:
    #         body
    #         return Response(content_type='application/json', body=body)
    #     except Exception as e:
    #         body = json.dumps({'status': 'failure', 'reason': str(e)})
    #         return Response(content_type='application/json', body=body, status=500)

    # # endregion

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

