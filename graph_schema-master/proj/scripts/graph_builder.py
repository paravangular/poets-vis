import networkx as nx

import xml.sax
import json
import sys, os
from collections import defaultdict
from collections import deque

from scripts.graph.core import *
from scripts.graph.events import *
from scripts.graph.snapshots import *
from scripts.graph.load_xml import *



class MetisHandler():
	def __init__(self, name, graph, basedir = "data/metis/", nodes_per_part = 50):
		'''
		Metis input format:

		V E fmt ncon
		s w1 w2 ... wncon v1 e1 v2 e2 ... vk ek

		V E flags num_vertex_weights
		vertex_weights1 v2 w2 v3 w3 v4 w4...
		vertex_weights2 v3 w3 v4 w4 v5 w5...

		...

		in this particular configuration, only edge weights are taken into account
		vertices have no weights

		'''

		self.nodes_per_part = nodes_per_part
		self.graph = graph
		self.filename_base = basedir + name + "_metis_input_"
		self.flag = "001"
		self.num_node_weights = 0
		self.rows = defaultdict(list)
		self.nid_map = {}
		self.set_nparts()
		self.partition_counts = defaultdict(lambda : defaultdict(int))
		self.partition_counts["base"]["nodes"] = self.graph.number_of_nodes()
		self.partition_counts["base"]["edges"] = self.graph.number_of_edges()
		self.partition_counts["base"]["contents"] = set()

		for node in self.graph.nodes:
			self.partition_counts["base"]["contents"].add(node)

		self.parqueue = deque()
		self.parqueue.append("base")

		while self.parqueue:
			pid = self.parqueue.popleft()
			self.set_nodes(pid)
			self.set_edges(pid)
			self.execute_metis(pid)

	def set_nparts(self):
		nnodes = self.graph.number_of_nodes()
		self.nlevels = 1
		self.nparts = []

		while nnodes > self.nodes_per_part:
			self.nparts.append(self.nodes_per_part)
			nnodes = nnodes // self.nodes_per_part
			self.nlevels += 1

		self.nparts.append(nnodes)
		self.nparts.reverse()

		del self.nparts[-1]


	def set_nodes(self, part_id = "base"):
		self.rows[part_id] = [None] * (self.partition_counts[part_id]["nodes"] + 1)
		self.nid_map[part_id] = {}
		i = 1

		for node in self.partition_counts[part_id]["contents"]:
			if "nid" not in self.graph.nodes[node]:
				self.graph.nodes[node]["nid"] = {}
				
			self.graph.nodes[node]["nid"][part_id] = i
			self.nid_map[part_id][i] = node
			self.rows[part_id][i] = "" #{} {} {} ".format(dev["type"], dev["messages_sent"], dev["messages_received"])
			i += 1

	def set_edges(self, part_id = "base"):
		self.partition_counts[part_id]["edges"] = 0
		for id, edge in self.graph.edges.iteritems():
			src, dst = id.split(":")
			if src in self.partition_counts[part_id]["contents"] and dst in self.partition_counts[part_id]["contents"]:
				self.partition_counts[part_id]["edges"] += 1
				nsrc = self.graph.nodes[src]["nid"][part_id]
				ndst = self.graph.nodes[dst]["nid"][part_id]
				# workaround for half edge
				self.rows[part_id][nsrc] += "{} {} ".format(ndst, edge["weight"])
				self.rows[part_id][ndst] += "{} {} ".format(nsrc, edge["weight"])
				
	def write_metis_input_file(self, part_id = "base"):
		self.rows[part_id][0] = "{} {} {}".format(self.partition_counts[part_id]["nodes"], self.partition_counts[part_id]["edges"], self.flag)
		input_file = open(self.filename(part_id), "w")
		for row in self.rows[part_id]:
			input_file.write(row + "\n")

	def execute_metis(self, part_id = "base"):
		self.write_metis_input_file(part_id)
		os.system("gpmetis " + self.filename(part_id) + " " +  str(self.nparts[self.part_level(part_id)]))
		self.read_metis_partition(part_id)

	def read_metis_partition(self, part_id = "base"):
		i = 1
		level = self.part_level(part_id)
		if level < self.nlevels - 2:
			for p in range(self.nparts[level]):
				self.parqueue.append(part_id + "_" + str(p))

		with open(self.filename(part_id) + ".part." + str(self.nparts[level]), "r") as f:
			for line in f:
				if part_id == "base":
					new_pid = "base_" + line.strip()
					node = self.nid_map[part_id][i]
					self.graph.nodes[node]["partition_0"] = new_pid
				else:
					node = self.nid_map[part_id][i]
					new_pid = self.graph.nodes[node]["partition_" + str(level - 1)] + "_" + line.strip()
					self.graph.nodes[node]["partition_" + str(level)] = new_pid
				i += 1
				if new_pid not in self.partition_counts:
					self.partition_counts[new_pid]["contents"] = set()
				self.partition_counts[new_pid]["nodes"] += 1
				self.partition_counts[new_pid]["contents"].add(node)
		

	def filename(self, part_id):
		return self.filename_base + part_id


	def part_level(self, part_id):
		if part_id == "base":
			return 0
		else:
			return len(part_id.split("_")) - 1



class GraphBuilder():
	def __init__(self, complex_graph):
		self.levels = 1

		self.nodes = {}
		self.set_device_instances(complex_graph)

		self.edges = {}
		self.set_edge_instances(complex_graph)

	def number_of_nodes(self):
		return len(self.nodes)

	def number_of_edges(self):
		return len(self.edges)

	def set_device_instances(self, graph):
		i = 0
		for id, dev in graph["device_instances"].iteritems():
			self.nodes[id] = {}
			i += 1

	def set_edge_instances(self, graph):
		for edge in graph["edge_instances"]:
			edge_id = min(edge["source"], edge["target"]) + ":" + max(edge["source"], edge["target"])

			if edge_id in self.edges:
				self.edges[edge_id]["weight"] += 1
			else:
				self.edges[edge_id] = {"weight": 1}

'''

create a partition for every event timestamp (if possible, if not, aggregate event timestamp)
	- combine events - aggregate by "seq" or "time" 1000
	- use --snapshot queue_sim/epoch_sim
	- list of events occurring between each snapshot

main view level 0:
	- biggest partition (4 levels ~ 100 nodes each, one tenth of all events aggregate)
	- 10 steps timestamp explorer ("from time a to b")
	- user can click on a node cluster, gets taken to subview

subview level 1:
	- one hundredth of all events aggregate stepper

subview level 2:
	- min(one thousandth of all events aggregate, 100) events



node weights: number of messages sent/received/both
edge weights: number of messages sent along edge (bidirectional)



TABLES
up to 3 partition levels x 10 snapshots: aggregate/average/sum properties of devices in each partition (integers only)
	level_0_time_0 level_0_time_1 ...
	level_1_time_0 ...

deepest level:
	device_instance: stores devices after init
	events: all events, can filter events based on time so no need for separate tables


SCHEMA
device_instance
id type [properties_type_1 properties_type_2...] [state_type_1 state_type_2...] msg_sent msg_recv

'''