'''
Code Author: Peng, Caikun
File Name: ryuController.py
Create Date: 17/07/2024 
Last Edit Date: 18/07/2024
Description: run `ryu-manager` command with several apps
Dependencies: subprocess
'''

import subprocess

ryu_apps = [
    # 'ryuController.py',
    'simple_switch_13.py',
    'ofctl_rest.py',    
    'rest_topology.py',
    'rest_conf_switch.py',
    'rest_port.py',
]

command = ['ryu-manager'] + ryu_apps

# print(command)

process = subprocess.Popen(command)
