"""
Code Author: Peng, Caikun
Create Date: 02/06/2024 
Last Edit Date: 03/06/2024
File Name: lab_1_part_a.py
Description: Functions of M/M/1 queue modle.
Dependencies: lab_1_functions, numpy, argparse, time
"""

import lab_1_functions as f
import numpy as np
import argparse
import time

def main(_lambda, npkts, fifo_len):
    print("Start Running")
    start_time = time.time()

    # Create log files
    log_file = f'log/sim_lambda_{_lambda}_npkts_{npkts}_Qlen_{fifo_len}.log'
    pkt_file = f'log/pkt_lambda_{_lambda}_npkts_{npkts}.log'
    sum_file = f'log/sum_lambda_{_lambda}_npkts_{npkts}_Qlen_{fifo_len}.log'
    open(log_file, 'w').close()
    open(pkt_file, 'w').close()
    open(sum_file, 'w').close()

    # Initial sim parameter
    source  = f.Source(_lambda,npkts)
    packets = source.generate()
    fifo   = f.Queue(log_file, fifo_len)
    server = f.Server(log_file)
    
    packets_served = []
    packet_index = 0
    packet_end   = 0
    service_flag = None

    # Time setting
    time_total = 2 * npkts
    clk = 0
    while clk < time_total:
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
    parser.add_argument("--_lambda",type=float, default=1,       help="lambda")
    parser.add_argument("--npkts",  type=int,   default=1000000, help="npkts")
    parser.add_argument("--queue",  type=int,   default=1000000, help="Queue length")

    # Parse the arguments
    args = parser.parse_args()

    # Access the arguments
    _lambda = args._lambda
    npkts = args.npkts
    fifo_len = args.queue

    main(_lambda, npkts, fifo_len)