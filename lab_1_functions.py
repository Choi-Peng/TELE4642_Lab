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

sys_clk = 0 

class system_clk:
	def __init__(self, clk=0):
		global sys_clk 
		sys_clk = clk
	
	def __str__(self):
		return "Current system time: {}".format(f"{sys_clk:.3f}")

class Packet:
	def __init__(self, packet_index, time_arrivel, packet_size):
		self.index     = packet_index
		self.arrival   = time_arrivel
		self.departure = None
		self.size      = packet_size

	def __str__(self):
		global sys_clk
		return "Current time: {}\t Index: {}\t Packet size: {}\t Arrival time: {}\t Departure time: {}"\
				.format(f"{sys_clk:.3f}", self.index, self.size, self.arrival, self.departure)

class Source:
	def __init__(self, _lambda = 1, npkts = 1000000, size = 1250):
		self._lambda = _lambda
		self.packet_count = npkts
		self.packets = []
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
			self.packets.append(packet)
			
		return self.packets

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
	def __init__(self, service_rate = 1250):
		# The server can process 10Gbps -> 10*10^9 bps -> 10*10^3 bits per us -> 1250 Bytes per us
		self.service_rate = service_rate
		self.current_time = 0
		self.packet = None
		self.state_current = "INITIAL"
		self.state_next = "INITIAL"
		self.state_falg = None
		self.time_flag = 1
		self.time_temp = 0

	def service(self, queue):

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
						self.state_next = "INITIAL"
					else:
						self.state_next = "SERVE"
				case _:
					self.state_next = "INITIAL"

		def state_initial(self):
			self.packet = None
			self.state_falg = None
			self.time_flag = 1
			self.time_temp = 0

		def state_get_packet(self, queue):
			packet_temp = queue.extract()
			if packet_temp != None:
				self.packet = packet_temp
				self.state_falg = "packet_getted"

		def state_serve(self):
			self.current_time = sys_clk
			if self.time_flag:
				self.time_temp = self.current_time
				self.service_time = round(self.packet.size / self.service_rate, 3)
				self.time_flag = 0
		
			time_delta = self.current_time - self.time_temp
			if  time_delta >= self.service_time:
				self.packet.departure = f"{self.current_time:.3f}"
				print(self.packet)
				self.state_falg = "packet_served"
		
		match self.state_current:
			case "INITIAL":
				state_initial(self)
			case "GET_PACKET":
				state_get_packet(self, queue)
			case "SERVE":
				state_serve(self)
			case _:
				state_initial(self)
		state_transfer(self)
		state_update(self)