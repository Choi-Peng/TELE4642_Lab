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
		return "Index: {} \t Packet size: {} \t Arrival time: {} \t Departure time: {} \t Spent {} us"\
			.format(self.index, self.size, self.arrival, self.departure, self.spent)

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
			arrival_time = round(self.current_time + inter_arrival_time, 2)
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
		self.num_Q = [0 for i in range(12)]
		self.log_file = log_file

	def insert(self, packet):
		if len(self.queue) >= self.size:
			self.dropped_count += 1
		else: 
			n = len(self.queue)
			self.queue.append(packet)
			with open(self.log_file, 'a') as f:
				f.write("Time: {} ARRIVAL    Index: {} Packet size:{} Find {} packets in the Queue\n"\
					.format(f"{sys_clk:<12.3f}", f"{packet.index:<6}", f"{packet.size:<6}", n))
			# print("Time: {} ARRIVAL    Index: {} Packet size:{} Find {} packets in the Queue"\
			# 	.format(f"{sys_clk:<12.3f}", f"{packet.index:<6}", f"{packet.size:<6}", n))
			if n < 11:
				self.num_Q[n] += 1
			else:
				self.num_Q[11] += 1

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
						self.state_next = "GET_PACKET"
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
				# print(packet_temp)
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
				# self.state_falg = "packet_served"
				self.packet_served += 1
				with open(self.log_file, 'a') as f:
					f.write("Time: {} DEPARTURE  Index: {} Packet size:{} Spent {} us in the system\n"\
						.format(f"{sys_clk:<12.3f}", f"{self.packet.index:<6}", f"{self.packet.size:<6}", f"{self.service_time:.3f}"))
				# print("Time: {} DEPARTURE  Index: {} Packet size:{} Spent {} us in the system"\
				# 	.format(f"{sys_clk:<12.3f}", f"{self.packet.index:<6}", f"{self.packet.size:<6}", f"{self.packet.spent:.3f}"))
				state_initial(self)
				self.state_falg = "packet_served"

		# print(f"Current State: {self.state_current}")
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
		N_total = self.packet_served
		T_total = 0
		for i in range(len(packets)):
			if packets[i].spent != None:
				T_total += packets[i].spent
		T  = T_total / N_total
		N  = 0
		n  = queue.num_Q
		P  = [0 for i in range(12)]
		Pn = [0 for i in range(12)]
		for i in range(len(n)):
			P[i] = (n[i]/N_total)
			if P[i] < 10 ** (-5):
				Pn[i] = f"{P[i]*(10**6):.3f}u" # u%
			elif P[i] < 10 ** (-2): 
				Pn[i] = f"{P[i]*(10**3):.3f}m" # m%
			else:
				Pn[i] = f"{P[i]:.3f}"          #  %
			N += P[i] * n[i]

		with open(sum_file, 'a') as f:
			f.write(f"Summary:\n")
			f.write(f"-------------------------------------------\n")
			f.write(f"average number of packets in the system N: {N:.2f}\n")
			f.write(f"average time spent by a packet in the system T: {T:.3f} us\n")
			f.write(f"probability P(n) (%) that an arriving packet finds n packets already in the system:\n")
			f.write(f"{"   n:":<8}{"0":<8}{"1":<8}{"2":<8}{"3":<8}{"4":<8}{"5":<8}{"6":<8}{"7":<8}{"8":<8}{"9":<8}{"10":<8}{">10":<8}Total \n")
			f.write(f"{" num:":<8}{n[0]:<8}{n[1]:<8}{n[2]:<8}{n[3]:<8}{n[4]:<8}{n[5]:<8}{n[6]:<8}{n[7]:<8}{n[8]:<8}{n[9]:<8}{n[10]:<8}{n[11]:<8}{sum(n)}\n")
			f.write(f"{"P(n):":<8}{Pn[0]:<8}{Pn[1]:<8}{Pn[2]:<8}{Pn[3]:<8}{Pn[4]:<8}{Pn[5]:<8}{Pn[6]:<8}{Pn[7]:<8}{Pn[8]:<8}{Pn[9]:<8}{Pn[10]:<8}{Pn[11]:<8}{sum(P)}\n")

		print("\nSummary:")
		print("-------------------------------------------")
		print(f"average number of packets in the system N: {N:.2f}")
		print(f"average time spent by a packet in the system T: {T:.3f} us")
		print(f"probability P(n) (%) that an arriving packet finds n packets already in the system: ")
		print(f"{"   n:":<8}{"0":<8}{"1":<8}{"2":<8}{"3":<8}{"4":<8}{"5":<8}{"6":<8}{"7":<8}{"8":<8}{"9":<8}{"10":<8}{">10":<8}Total \n")
		print(f"{" num:":<8}{n[0]:<8}{n[1]:<8}{n[2]:<8}{n[3]:<8}{n[4]:<8}{n[5]:<8}{n[6]:<8}{n[7]:<8}{n[8]:<8}{n[9]:<8}{n[10]:<8}{n[11]:<8}{sum(n)}\n")
		print(f"{"P(n):":<8}{Pn[0]:<8}{Pn[1]:<8}{Pn[2]:<8}{Pn[3]:<8}{Pn[4]:<8}{Pn[5]:<8}{Pn[6]:<8}{Pn[7]:<8}{Pn[8]:<8}{Pn[9]:<8}{Pn[10]:<8}{Pn[11]:<8}{sum(P)}\n")
