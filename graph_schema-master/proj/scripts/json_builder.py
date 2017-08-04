from scripts import helper
import json


def safe_list_get (l, idx, default):
  try:
    return l[idx]
  except IndexError:
    return default


class JSONBuilder():
	def __init__(self, part_id, init = 1, epoch = 0):
		self.part_id = part_id
		self.epoch = epoch
		self.init = init
		level = len(self.part_id.split("_")) - 1
		nlevels = helper.execute_query("SELECT max FROM levels")
		node_prop = [row[1] for row in helper.execute_query("PRAGMA table_info(device_states)")] + ["parent"]
		edge_prop = ["source", "target", "count"]

		if level < nlevels[0][0] - 1:
			iquery = ("SELECT * FROM device_states_aggregate_{0} AS states ".format(level) + 
				" JOIN device_properties_aggregate_{0} AS properties ON properties.partition_id = states.partition_id".format(level) + 
				" WHERE init = ? AND epoch = ? AND states.parent = ? ")
			interior = helper.execute_query(iquery, [self.init, self.epoch, self.part_id])
		else:
			iquery = ("SELECT * FROM device_states AS states" + 
				" JOIN device_properties AS properties ON properties.id = states.id" + 
				" JOIN (SELECT id FROM device_partitions WHERE partition_{} = ?) AS parts ON states.id = parts.id"
				" WHERE init = ? AND epoch = ?".format(level - 1))
			interior = helper.execute_query(iquery, [self.part_id, self.init, self.epoch])

		interior_edges = helper.execute_query("SELECT source, target, count FROM partition_edges_{} WHERE parent = ? AND source != target".format(level), [self.part_id])
		border = []
		border_edges = []
		if level > 0:
			border = helper.execute_query("SELECT DISTINCT lower_level FROM interpartition_edges_{}_{} WHERE parent = ?".format(level, level + 1), [self.part_id])
			border_edges = helper.execute_query("SELECT higher_level, lower_level, count FROM interpartition_edges_{}_{} WHERE parent = ?".format(level, level + 1), [self.part_id])
		nodes = interior + border

		nodes_json = []
		for node in nodes:
			n = {}

			for i in range(len(node_prop)):
				n[node_prop[i]] = safe_list_get(node, i, None)

			nodes_json.append(n)

		edges_json = []
		# self.nodes_csv = ["|".join(map(str, [x for x in node])) for node in nodes]

		edges = interior_edges + border_edges

		for edge in edges:
			e = {}
			for i in range(len(edge_prop)):
				e[edge_prop[i]] = safe_list_get(edge, i, None)

			edges_json.append(e)

		self.json = {"nodes": nodes_json, "edges": edges_json}
		print(self.json)



