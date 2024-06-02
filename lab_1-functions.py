"""
Code Author: Peng, Caikun
Create Date: 01/06/2024 
File Name: lab_1-functions.py
Vision: 
Description: Functions of M/M/1 queue modle. including 'Source', 'Queue'.
Dependencies: numpy
"""

import numpy as np

class packet:
	def __init__(self, packet_index, time_arrivel, packet_size):
		self.index     = packet_index
		self.arrival   = time_arrivel
		self.departure = None
		self.size      = packet_size

	def __str__(self):
		return "Index: {}, Arrival time: {}, Packet size: {}".format(self.index, self.arrival, self.size)

class source:
	def __init__(self, _lambda = 1, npkts = 1000000, size = 1250):
		self._lambda = _lambda
		self.packet_count = npkts
		self.size = size
		self.generated_packets = 0
		self.current_time = 0
	
	def generate(self):
		while self.generated_packets < self.packet_count:
			packet_size = round(np.random.exponential(self.size))
			inter_arrival_time = np.random.exponential(1 / self._lambda)
			arrival_time = round(self.current_time + inter_arrival_time, 3)
			packets = packet(self.generated_packets, arrival_time, packet_size)
			self.generated_packets += 1
			self.current_time = arrival_time
			yield packets

s=source(1,10)
for packets in s.generate():
	print(packets)

class Queue:
	def __init__(self, size = 1):
		self.size  = size
		self.queue = []
		self.dropped_count = 0 

	def insert(self, item):
		if len(self.queue) >= self.size:
			self.dropped_count += 1
		else: 
			self.queue.append(item)
	
	def extract(self):
		if len(self.queue) != 0:
			return self.queue.pop(0)

	def dropped(self):
		return self.dropped_count

class server:
	def __init__(self, queue):
		self.service_rate = 10 * (10**9)  # The server can process 10Gbps
		self.queue = queue
		self.current_time = 0