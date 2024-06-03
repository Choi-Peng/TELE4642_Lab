"""
Code Author: Peng, Caikun
Create Date: 01/06/2024 
Last Edit Date: 03/06/2024
File Name: lab_1_functions.py
Description: Functions of M/M/1 queue modle.
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
		self.spent     = None
		self.size      = packet_size

	def __str__(self):
		global sys_clk
		return "Index: {} \t Packet size: {} ".format(self.index, self.size)

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
			inter_arrival_time = np.random.poisson(1 / self._lambda)
			# inter_arrival_time = np.random.exponential(1 / self._lambda)
			arrival_time = round(self.current_time + inter_arrival_time, 3)
			packet = Packet(self.generated_packets, arrival_time, packet_size)
			self.generated_packets += 1
			self.current_time = arrival_time
			self.packets.append(packet)
		
		return self.packets

class Queue:
	def __init__(self, log_file, size):
		self.size  = size
		self.queue = []
		self.dropped_count = 0 
		self.num_Q = [0 for i in range(11)]
		self.log_file = log_file

	def insert(self, item):
		if len(self.queue) >= self.size:
			self.dropped_count += 1
		else: 
			n = len(self.queue)
			self.queue.append(item)
			with open(self.log_file, 'a') as f:
				f.write(f"Time: {sys_clk:.3f} \tARRIVAL\t\t{item}\t{n} packets in the Queue\n")
			print(f"Time: {sys_clk:.3f} \tARRIVAL\t\t{item}\t{n} packets in the Queue")
			if n < 10:
				self.num_Q[n] += 1
			else:
				self.num_Q[10] += 1

	def extract(self):
		if len(self.queue) != 0:
			return self.queue.pop(0)

	def dropped(self):
		return self.dropped_count

	def __str__(self):
		return self.queue[0]

class Server:
	def __init__(self, log_file, service_rate = 1250):
		# The server can process 10Gbps -> 10*10^9 bps -> 10*10^3 bits per us -> 1250 Bytes per us
		self.service_rate = service_rate
		self.current_time = 0
		self.packet = None
		self.packet_served = 0
		self.state_current = "INITIAL"
		self.state_next = "INITIAL"
		self.state_falg = None
		self.time_flag = 1
		self.time_temp = 0
		self.service_end = 0
		self.log_file = log_file

	def service(self, queue, service_flag):
		"""
		State Transfer
		# INITIAL -> GET_PACKET -> SERVE -> GET_PACKET
		"""

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
						if service_flag == "END":
							self.service_end = 1
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
				self.packet.spent = self.current_time - self.packet.arrival
				self.state_falg = "packet_served"
				self.packet_served += 1
				with open(self.log_file, 'a') as f:
					f.write(f"Time: {sys_clk:.3f} \tDEPARTURE\t{self.packet}\tspent {self.service_time:.3f} us in the system\n")
				print(f"Time: {sys_clk:.3f} \tDEPARTURE\t{self.packet}\tspent {self.packet.spent:.3f} us in the system")
		
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

	def summary(self, sum_file, queue, packets):
		N = self.packet_served
		T_total = 0
		for i in range(len(packets)):
			if packets[i].spent != None:
				T_total += packets[i].spent
		T = T_total / N
		n = queue.num_Q
		P = [0 for i in range(11)]
		Pn = [0 for i in range(11)]
		for i in range(len(n)):
			P[i] = (n[i]/N) * 100  
			if P[i] < 10 ** (-3): 
				Pn[i] = f"{P[i]*(10**3):.3f}m" # m%
			else:
				Pn[i] = f"{P[i]:.3f}"          # %

		with open(sum_file, 'a') as f:
			f.write(f"Summary:\n")
			f.write(f"-------------------------------------------\n")
			f.write(f"average number of packets in the system N: {N}\n")
			f.write(f"average time spent by a packet in the system T: {T:.3f}\n")
			f.write(f"probability P(n) (%) that an arriving packet finds n packets already in the system:\n")
			f.write(f"n:\t\t0\t\t1\t\t2\t\t3\t\t4\t\t5\t\t6\t\t7\t\t8\t\t9\t\t>= 10\tTotal \n")
			f.write(f"num:\t{n[0]}\t\t{n[1]}\t\t{n[2]}\t\t{n[3]}\t\t{n[4]}\t\t{n[5]}\t\t{n[6]}\t\t{n[7]}\t\t{n[8]}\t\t{n[9]}\t\t{n[10]}\t\t{sum(n)}\n")
			f.write(f"P(n):\t{Pn[0]}\t{Pn[1]}\t{Pn[2]}\t{Pn[3]}\t{Pn[4]}\t{Pn[5]}\t{Pn[6]}\t{Pn[7]}\t{Pn[8]}\t{Pn[9]}\t{Pn[10]}\t{sum(P)}\n")

		print("\nSummary:")
		print("-------------------------------------------")
		print(f"average number of packets in the system N: {N}")
		print(f"average time spent by a packet in the system T: {T:.3f}")
		print(f"probability P(n) (%) that an arriving packet finds n packets already in the system: ")
		print(f"   n:\t0\t1\t2\t3\t4\t5\t6\t7\t8\t9\t>= 10\tTotal")
		print(f" num:\t{n[0]}\t{n[1]}\t{n[2]}\t{n[3]}\t{n[4]}\t{n[5]}\t{n[6]}\t{n[7]}\t{n[8]}\t{n[9]}\t{n[10]}\t{sum(n)}")
		print(f"P(n):\t{Pn[0]}\t{Pn[1]}\t{Pn[2]}\t{Pn[3]}\t{Pn[4]}\t{Pn[5]}\t{Pn[6]}\t{Pn[7]}\t{Pn[8]}\t{Pn[9]}\t{Pn[10]}\t{sum(P)}")
		#Here you need to plot P(n) for n from 0 to 10
		#X axis would be 0 to 10
		#Y axis would be P(n)