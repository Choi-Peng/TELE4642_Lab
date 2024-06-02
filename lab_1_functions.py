"""
Code Author: Peng, Caikun
Create Date: 01/06/2024 
Last Edit Date: 02/06/2024
File Name: lab_1-functions.py
Vision: 
Description: Functions of M/M/1 queue modle. including 'Source', 'Queue'.
Dependencies: numpy
"""

import numpy as np

global clk 

class Packet:
	def __init__(self, packet_index, time_arrivel, packet_size):
		self.index     = packet_index
		self.arrival   = time_arrivel
		self.departure = None
		self.size      = packet_size

	def __str__(self):
		return "Index: {}, Arrival time: {}, Packet size: {}".format(self.index, self.arrival, self.size)

class Source:
	def __init__(self, _lambda = 1, npkts = 1000000, size = 1250):
		self._lambda = _lambda
		self.packet_count = npkts
		self.size = size
		self.generated_packets = 0
		self.current_time = 0
	
	def generate(self):
		while self.generated_packets < self.packet_count:
			""" Packet sizes are exponentially distributed with a mean size of 1250 Bytes. """
			packet_size = round(np.random.exponential(self.size))
			""" The source generates packets as a Poisson process at a specified rate lambda. """
			# inter_arrival_time = np.random.poisson(1 / self._lambda)
			inter_arrival_time = np.random.exponential(1 / self._lambda)
			arrival_time = round(self.current_time + inter_arrival_time, 3)
			packet = Packet(self.generated_packets, arrival_time, packet_size)
			self.generated_packets += 1
			self.current_time = arrival_time
			yield packet

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

	def __str__(self):
		return self.queue[0]

class Server:
	"""
	State Transfer
	# INITIAL -> GET_PACKET -> SERVE -> GET_PACKET
	"""
	def __init__(self):
		self.service_rate = 10 * (10**9)  # The server can process 10Gbps
		self.current_time = 0
		self.state_current = "INITIAL"
		self.state_next = "INITIAL"
		self.state_falg = None

	def state_update(self): 
		self.state_current = self.state_next

	def state_transfer(self):
		match self.state_current:
			case "INITIAL":
				self.state_next = "GET_PACKET"
			case "GET_PACKET":
				if self.state_falg == "packet_getted":
					self.state_next = "SERVE"
				else: 
					self.state_next = "GET_PACKET"
			case "SERVE":
				if self.state_falg == "packet_served":
					self.state_next = "GET_PACKET"
				else:
					self.state_next = "SERVE"
			case _:
				self.state_next = "INITIAL"

	def state_initial(self):
		__init__()

	def state_get_packet(self, packet):
		packet_temp = packet
		if packet_temp != None:
			self.packet = packet_temp
			self.state_falg = "packet_getted"

	def state_serve(self):
		service_time = self.packet.size / self.service_rate

