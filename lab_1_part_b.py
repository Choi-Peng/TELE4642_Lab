"""
Code Author: Peng, Caikun
Create Date: 03/06/2024 
Last Edit Date: 03/06/2024
File Name: lab_1_part_b.py
Description: Main program of lab 1 - part b
Dependencies: lab_1_functions, argparse, numpy, time
"""

import lab_1_functions as f
import argparse
import numpy as np
import time

class Source:
    def __init__(self):
        self.trace_temp = []
        self.packets = []
        self.size = 0
        self.generated_packets = 0
        self.current_time = 0

    def generate(self, file_name):
        with open(file_name, 'r') as file:
            for line in file:
                self.trace_temp = line.strip().split()        
                inter_arrival_time = float(self.trace_temp[0])
                packet_size = int(self.trace_temp[1])
                arrival_time = round(self.current_time + inter_arrival_time, 2)
                packet = f.Packet(self.generated_packets, arrival_time, packet_size)
                self.generated_packets += 1
                self.current_time = arrival_time
                self.packets.append(packet)
		
        return self.packets

# for pkt in packets:
#     print(pkt)

def main(file_name):
    print("Start Running")
    start_time = time.time()

    # Create log files
    log_file = f'E:/UNSW/24_T2/TELE4642/Lab/Lab_1/log/sim_{file_name}.log'
    pkt_file = f'E:/UNSW/24_T2/TELE4642/Lab/Lab_1/log/pkt_{file_name}.log'
    sum_file = f'E:/UNSW/24_T2/TELE4642/Lab/Lab_1/log/sum_{file_name}.log'
    open(log_file, 'w').close()
    open(pkt_file, 'w').close()
    open(sum_file, 'w').close()

    # Initial sim parameter
    source  = Source()
    print("Generating packets")
    start_generate_time = time.time()
    packets = source.generate(f"lab_1_part_b_{file_name}.test")
    end_generate_time = time.time()
    print(f"Generated, using: {end_generate_time - start_generate_time}s.")
    npkts   = len(packets)
    fifo    = f.Queue(log_file, npkts)
    server  = f.Server(log_file)

    packets_served = []
    packet_index = 0
    packet_end   = 0
    service_flag = None

    # Time setting
    clk = 0

    while 1:
        f.system_clk(clk)

        if packet_index < npkts:
            packet_current = packets[packet_index]
            if clk >= packet_current.arrival: 
                fifo.insert(packet_current)
                packet_index += 1
        else:
            packet_current = None    
            packet_end = 1
            if len(fifo.queue) == 0: 
                service_flag = "END"

        server.service(fifo, service_flag)
        if server.service_end:
            server.summary(sum_file, fifo, packets)
            break

        clk += 0.001

    np.savetxt(pkt_file, packets, fmt='%s', delimiter='\t')

    # for pkt in range(len(packets)):
    #     with open(pkt_file, 'a') as pkts:
    #         pkts.write(f"{packets[pkt]}\tArrival Time: {packets[pkt].arrival}  \tDeparture Time: {packets[pkt].departure} \tSpent: {packets[pkt].spent:.3f}\n")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"End Running. Time Usage: {elapsed_time} s")

if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser()
    
    # Add arguments
    parser.add_argument("--traceNumber", type=str, default='trace2',help="traceNumber")

    # Parse the arguments
    args = parser.parse_args()

    # Access the arguments
    file_name = args.traceNumber

    # Call main function with file_name
    main(file_name)