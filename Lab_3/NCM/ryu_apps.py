import subprocess

# 定义要运行的Ryu应用程序脚本
ryu_apps = [
    'ryuController.py',
    'rest_topology.py',
    'rest_conf_switch.py',
    'rest_conf_port.py',
    'ofctl_rest.py'
]

# 启动每个Ryu应用程序脚本
processes = []

for app in ryu_apps:
    # 使用subprocess.Popen启动每个脚本
    process = subprocess.Popen(['ryu-manager', app])
    processes.append(process)

# 等待所有进程完成
for process in processes:
    process.wait()
