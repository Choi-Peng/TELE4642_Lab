"""
Code Author: Peng, Caikun
Create Date: 03/06/2024 
Last Edit Date: 03/06/2024
File Name: lab_1_part_b.py
Description: Main program of lab 1 - part b
Dependencies: lab_1_functions
"""

import lab_1_functions as f

class Trace:
    def __init__(self):
        self.trace_temp = []
        self.dt    = []
        self.size  = []

    def read(self,file_name):
        i=0
        with open(file_name, 'r') as file:
            for line in file:
                self.trace_temp.append(line.strip().split())
                self.dt.append(float(self.trace_temp[i][0]))
                self.size.append(int(self.trace_temp[i][1]))
                i += 1

trace = Trace()
trace.read("lab_1_part_b_trace1.test")
print(trace.trace_temp)