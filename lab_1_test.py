import lab_1_functions as f
import numpy as np

_lambda = 1
n = 100
source = f.Source(_lambda,n)
packets = source.generate()
packets_served = []
fifo = f.Queue(n)
server = f.Server()

# for i in range(len(packets)):
#     print(packets[i])

t = np.arange(0, 200, 0.001)
packet_index = 0
for clk in t:
    f.system_clk(clk)
    if packet_index < n:
        packet_current = packets[packet_index]
        if clk >= packet_current.arrival:
            fifo.insert(packet_current)
            # print(packet_current)
            packet_index += 1
    else:
        packet_current = None    
    # print(packet_current)
    # print(f.system_clk(clk))
    server.service(fifo)
