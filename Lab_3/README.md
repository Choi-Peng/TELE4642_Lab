# Webpage

The Project Webpage: [TELE4642 Project - Network Control and Monitoring](https://sites.google.com/view/tele4642-project-ncm)

# Basics 

## Topology
The topology of the network in this project is like:
``` markdown
┌──────┐      ╭─────────────────╮  REST API  ╭─────────────╮
│ Host ├──┐   | Ryu Controller  |<───────────| Application |
└──────┘  |   ╰────────╥────────╯            ╰──────┬──────╯
┌──────┐  |            ║                            | 
│ Host ├──┤   OpenFlow ╠═══════════════════════╗    |              ┌──────────┐
└──────┘  |            ║                       ║    |          ┌───┤ Internet |
┌──────┐  |       ┌────╨────┐           ┌──────╨────┴──────┐   |   └──────────┘
│ Host ├──┼───────┤ Switch  ├───────────┤ Monitor/Firewall ├───┤
└──────┘  |       └─────────┘           └─────────┬────────┘   |   ┌──────────────┐
          |                                       |            └───┤ Local Server |
 ......  ...                                      |                └──────────────┘
          |                                  ╭────┴────╮
┌──────┐  |                                  | Logger  |
│ Host ├──┘                                  ╰─────────╯
└──────┘  
```
where
- **Host**: Host node represents the terminal device in the network.
- **Switch**: Switch node connecta multiple hosts and manage traffic.
- **Monitor/Firewall**: Monitoring or firewall devices for network security and traffic monitoring.
- **Internet** and **Local Server**: Indicates the external Internet and local server.
- **Ryu Controller**: Controller communicates with the switch and monitor through the OpenFlow protocol.
- **Application**: Application sents REST API based information in ryu controller
- **Logger**: Logger records network activity logs (if necessary).

## Software versions
The versions of software used in this project are:

| Software | Version |
| -------- | ------- |
| Python   | 3.8.10  |
| Mininet  | 2.3.0   |
| Ryu      | 4.34    |

# Scripts Description
## net.py

[This script](NCM/net.py) creates a network topo with IPv6 disabled switches and hosts.

Run script:
``` cmd 
python3 net.py
```

## ryu_apps.py

[This script](NCM/ryu_apps.py) is used to run `ryu-manager` command with several controllers including REST controllers and switch controller below:

REST controllers: `rest_topology.py`, `rest_conf_switch.py`, `rest_conf_port.py`, and `ofctl_rest.py`.

Switch controller: `ryuController.py`.

Run script: 
``` cmd 
python3 ryu_apps.py
```
## rest_topology.py 

It defined some REST API to get topology information. See how to use it in [this script](NCM/rest_topology.py).

Import from [Ryu repository](https://github.com/faucetsdn/ryu/blob/master/ryu/app/rest_topology.py). 

Modification:
- Removed `/v1.0` from all `/v1.0/topology` endpoints to simplify command input.

## rest_conf_switch.py

It defined some REST API for switch configuration. See how to use it in [this script](NCM/rest_conf_switch.py).

Import from [Ryu repository](https://github.com/faucetsdn/ryu/blob/master/ryu/app/rest_conf_switch.py). 

Modification:
- Removed `/v1.0` from all `/v1.0/conf` endpoints to simplify command input. 
- Added import for `WSGIApplication` in `from ryu.app.wsgi import ControllerBase` on line 28.
- Added `'wsgi': WSGIApplication` on line 151.

## ofctl_rest.py 

It defined some REST API to retrieve the switch stats. See how to use it in [this script](NCM/ofctl_rest.py).

Import from [Ryu repository](https://github.com/faucetsdn/ryu/blob/master/ryu/app/ofctl_rest.py). 
