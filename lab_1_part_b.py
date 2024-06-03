"""
Code Author: Peng, Caikun
Create Date: 03/06/2024 
Last Edit Date: 03/06/2024
File Name: lab_1_part_b.py
Description: Main program of lab 1 - part b
Dependencies: lab_1_functions
"""

import lab_1_functions as f

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
                packet_size = self.trace_temp[1]
                arrival_time = round(self.current_time + inter_arrival_time, 2)
                packet = f.Packet(self.generated_packets, arrival_time, packet_size)
                self.generated_packets += 1
                self.current_time = arrival_time
                self.packets.append(packet)
		
        return self.packets

source = Source()
packets = source.generate("lab_1_part_b_trace1.test")

for pkt in packets:
    print(pkt)