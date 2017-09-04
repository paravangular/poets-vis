from scripts import helper
import json
from operator import itemgetter
from collections import defaultdict

def safe_list_get (l, idx, default):
  try:
    return l[idx]
  except IndexError:
    return default

class MetaBuilder():
	def __init__(self):
		self.max_level = helper.execute_query("SELECT max FROM meta_properties WHERE name = 'level'")
		self.max_time = helper.execute_query("SELECT max FROM meta_properties WHERE name = 'time'")

		ranges_query = "SELECT * FROM state_ranges"
		state_ranges = helper.execute_query(ranges_query)
		self.ranges_json = {}
		for state in state_ranges:
			self.ranges_json[state[0]] = {"min": state[1], "max": state[2]}

		prop_query = "SELECT * FROM device_types"
		device_types = helper.execute_query(prop_query)

		self.dev_json = {}
		for dev in device_types:
			self.dev_json[dev[0]] = {"states": dev[1], "properties": dev[2]}

		port_query = ("SELECT DISTINCT name FROM ports")
		message_type_query = ("SELECT DISTINCT message_type FROM ports")

		self.ports = dict([(p[0], None) for p in helper.execute_query(port_query)])
		self.message_types = dict([(m[0], None) for m in helper.execute_query(message_type_query)])

class JSONBuilder():
	def __init__(self, part_id, init = 1, epoch = 0):
		self.part_id = part_id
		self.epoch = epoch
		self.init = init
		level = len(self.part_id.split("_")) - 1
		nlevels = helper.execute_query("SELECT max FROM meta_properties WHERE name = 'level'")
		edge_prop = ["source", "target", "count"]

		if level < nlevels[0][0] - 1:
			node_prop = [row[1] for row in helper.execute_query("PRAGMA table_info(device_states_aggregate_{0})".format(level))] + [row[1] for row in helper.execute_query("PRAGMA table_info(device_properties_aggregate_{0})".format(level))] + ["parent"] 
			iquery = ("SELECT * FROM device_states_aggregate_{0} AS states ".format(level) + 
				" JOIN device_properties_aggregate_{0} AS properties ON properties.partition_id = states.partition_id".format(level) + 
				" WHERE init = ? AND epoch = ? AND states.parent = ? ")
			interior = helper.execute_query(iquery, [self.init, self.epoch, self.part_id])
		else:

			node_prop = [row[1] for row in helper.execute_query("PRAGMA table_info(device_states)")] + [row[1] for row in helper.execute_query("PRAGMA table_info(device_properties)")]
			iquery = ("SELECT * FROM device_states AS states" + 
				" JOIN device_properties AS properties ON properties.id = states.id" + 
				" JOIN (SELECT id FROM device_partitions WHERE partition_{} = ?) AS parts ON states.id = parts.id".format(level - 1) + 
				" WHERE init = ? AND epoch = ?")
			interior = helper.execute_query(iquery, [self.part_id, self.init, self.epoch])

		interior_edges = helper.execute_query("SELECT source, target, count FROM partition_edges_{} WHERE parent = ? AND source != target".format(level), [self.part_id])
		border = []
		border_edges = []
		if level > 0:
			border = helper.execute_query("SELECT DISTINCT lower_level FROM interpartition_edges_{}_{} WHERE parent = ?".format(level, level + 1), [self.part_id])
			border_edges = helper.execute_query("SELECT higher_level, lower_level, count FROM interpartition_edges_{}_{} WHERE parent = ?".format(level, level + 1), [self.part_id])
		nodes = interior + border


		nodes_json = {}
		for node in nodes:
			n = {}

			for i in range(len(node_prop)):
				if node_prop[i] == "partition_id":
					node_prop[i] = "id"
				
				if node_prop[i] not in n:
					n[node_prop[i]] = safe_list_get(node, i, None)

				n["messages_sent"] = 0
				n["messages_received"] = 0
				
			nodes_json[safe_list_get(node, 0, "unidentified")] = n

		print nodes[-1][0]

		edges_json = []
		# self.nodes_csv = ["|".join(map(str, [x for x in node])) for node in nodes]

		edges = interior_edges + border_edges

		for edge in edges:
			e = {}
			for i in range(len(edge_prop)):
				e[edge_prop[i]] = safe_list_get(edge, i, None)

			edges_json.append(e)

		self.json = {"nodes": nodes_json, "edges": edges_json}

		self.max_level = nlevels

		



class SnapshotJSONBuilder():
	def __init__(self, start, end, part_id):
		level = len(part_id.split("_")) - 1

		cols = [row[1] for row in helper.execute_query("PRAGMA table_info(device_states_aggregate_{})".format(level))]
		states = helper.execute_query("SELECT * FROM device_states_aggregate_{}".format(level) + 
									" WHERE parent = '{0}' AND epoch >= {1} AND epoch <= {2}".format(part_id, start - 1, end + 1))

		self.json = {"snapshots": []}

		for part in states:
			p = {}
			for i in range(len(cols)):
				p[cols[i]] = safe_list_get(part, i, None)

			self.json["snapshots"].append(p)
		

class EventJSONBuilder():
	def __init__(self, start, end, part_id):
		self.cols = [row[1] for row in helper.execute_query("PRAGMA table_info(events)")]
		for i in range(len(self.cols)):
			if self.cols[i] == "type":
				type_col = i
			if self.cols[i] == "send_id":
				send_event_col = i

		level = len(part_id.split("_")) - 2
		self.events = helper.execute_query("SELECT * FROM events" + 
								" JOIN (SELECT device_partitions.id FROM device_partitions" +
								" WHERE partition_{0} = '{1}') AS parts".format(level, part_id) + 
								" ON events.dev = parts.id" + 
								" WHERE time >= {0} AND time <= {1}".format(start - 1, end + 1))
		self.json = {"send": [], "recv": {}}

		for evt in self.events:
			e = {}
			for i in range(len(self.cols)):
				e[self.cols[i]] = safe_list_get(evt, i, None)
			
			if evt[type_col] == "send":
				self.json["send"].append(e)
			else:
				self.json["recv"][safe_list_get(evt, send_event_col, "unidentified")] = e

		self.json["send"].sort(key=itemgetter("time")) # potential bottleneck


class StepperJSONBuilder():
	def __init__(self, part_id, max_level):
		level = len(part_id.split("_")) - 1

		if level == max_level - 1:
			self.cols = [row[1] for row in helper.execute_query("PRAGMA table_info(device_states)")]
			query = ("SELECT * FROM device_states" + 
					" JOIN (SELECT device_partitions.id FROM device_partitions" + 
					" WHERE partition_" + str(level - 1) + " = '" + part_id + "') AS parts"
					" ON device_states.id = parts.id")

		else:
			self.cols = [row[1] for row in helper.execute_query("PRAGMA table_info(device_states_aggregate_{0})".format(level))]
			query = ("SELECT * FROM device_states_aggregate_{0}".format(level) + 
					" WHERE parent = '{0}'".format(part_id))

		self.snapshot = helper.execute_query(query)

		self.json = defaultdict(dict)
		for snapshot in self.snapshot:
			epoch = None
			s = {}
			for i in range(len(self.cols)):
				if self.cols[i] == "partition_id" or self.cols[i] == "id":
					id = safe_list_get(snapshot, i, "undefined")

				if self.cols[i] == "epoch":
					epoch = safe_list_get(snapshot, i, 0)

				s[self.cols[i]] = safe_list_get(snapshot, i, None)
			s["messages_sent"] = 0
			s["messages_received"] = 0

			self.json[epoch][id] = s




		