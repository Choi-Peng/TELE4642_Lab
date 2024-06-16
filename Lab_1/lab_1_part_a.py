"""
Code Author: Peng, Caikun
Create Date: 02/06/2024 
Last Edit Date: 05/06/2024
File Name: lab_1_part_a.py
Description: Main program of lab 1 - part a
Dependencies: lab_1_functions, numpy, argparse, time, os, shutil, tqdm
"""

import lab_1_functions as f
import numpy as np
import argparse
import time
import os
import shutil
from tqdm import tqdm

def recreate_directory(directory_path):
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)

    os.makedirs(directory_path)

def main(_lambda, npkts, fifo_len):
    print("Start Running")
    start_time = time.time()

    # Define log file address
    if fifo_len == 0:
        file_addr = f"E:/UNSW/24_T2/TELE4642/Lab/Lab_1/log/lambda_{_lambda}_npkts_{npkts}"
    else:
        file_addr = f"E:/UNSW/24_T2/TELE4642/Lab/Lab_1/log/lambda_{_lambda}_npkts_{npkts}_Qlen_{fifo_len}"
    recreate_directory(file_addr)

    f.log_init(file_addr)

    # Initial sim parameter
    source  = f.Source_part_a(_lambda,npkts)
    packets = source.generate()
    fifo    = f.Queue(fifo_len)
    server  = f.Server(npkts)
    
    packets_served = []
    packet_index = 0
    packet_end   = 0
    service_flag = "IDLE"
    packet_flag  = None

    # Time setting
    clk = 0

    # Progress bar
    packet_insert_progress = tqdm(range(npkts), desc="Packets insert progress", position=0, leave=True)
    packet_served_progress = tqdm(range(npkts), desc="Packets served progress", position=1, leave=True)
    # with tqdm(total=npkts) as pbar:
    while 1:
        f.System_clk(clk)
        
        # Start service
        service_flag = server.service(fifo, service_flag, packet_flag)
        if server.state_flag == "packet_served":
            packet_served_progress.update(1)
            
        # FIFO Queue
        if packet_index < npkts:
            packet_current = packets[packet_index]
            if clk >= packet_current.arrival: 
                fifo.insert(packet_current, service_flag)
                packet_index += 1
                packet_insert_progress.update(1)
        else:
            packet_current = None    
            packet_end = 1
            if len(fifo.queue) == 0: 
                packet_flag = "to_END"

        if server.service_end:
            server.summary(file_addr, f"lambda = {_lambda}", fifo, packets)
            break

        clk += 0.01 # us [packet arrival time] = 0.01 us

    pkt_file = f"{file_addr}/packets.txt"
    np.savetxt(pkt_file, packets, fmt='%s', delimiter='\t')
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"End Running. Time Usage: {elapsed_time} s")

if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser()
    
    # Add arguments
    parser.add_argument("--_lambda", type=float, default=1.0    , help="lambda"      )
    parser.add_argument("--npkts"  , type=int  , default=1000000, help="npkts"       )
    parser.add_argument("--queue"  , type=int  , default=0      , help="Queue length")

    # Parse the arguments
    args = parser.parse_args()

    # Access the arguments
    _lambda = args._lambda
    npkts = args.npkts
    fifo_len = args.queue

    print(f"lambda = {_lambda}")

    main(_lambda, npkts, fifo_len)