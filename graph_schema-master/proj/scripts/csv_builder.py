from scripts import helper

class CSVBuilder():
	def __init__(self, part_id, epoch = 0):
		self.part_id = part_id
		self.epoch = epoch

	def get(self):
		if self.part_id == "base":
			level = 0
		else:
			level = len(self.part_id.split("_")) - 1

		nlevels = helper.execute_query("SELECT max FROM levels")

		if level < nlevels[0][0] - 1:
			iquery = ("SELECT * FROM device_states_aggregate_{0} AS states ".format(level) + 
					" JOIN device_properties_aggregate_{0} AS properties ON properties.partition_id = states.partition_id".format(level) + 
					" WHERE epoch = ? AND states.parent = ? ")

			interior = helper.execute_query(iquery, [self.epoch, self.part_id])


		else:
			iquery = ("SELECT * FROM device_states AS states" + 
					" JOIN device_properties AS properties ON properties.id = states.id" + 
					" JOIN (SELECT id FROM device_partitions WHERE partition_{} = ?) AS parts ON states.id = parts.id"
					" WHERE epoch = ?".format(level - 1))

			interior = helper.execute_query(iquery, [self.part_id, self.epoch])


		interior_edges = helper.execute_query("SELECT source, target, count FROM partition_edges_{} WHERE parent = ? AND source != target".format(level), [self.part_id])
		border = helper.execute_query("SELECT DISTINCT lower_level FROM interpartition_edges_{}_{} WHERE parent = ?".format(level, level + 1), [self.part_id])
		border_edges = helper.execute_query("SELECT source, target, count FROM partition_edges_{} WHERE parent = ? AND source != target".format(level), [self.part_id])
		
		nodes = interior + border

		nodes_csv = ["|".join(map(str, [x for x in node])) for node in nodes]
		edges = interior_edges + border_edges

		edges_csv = ["|".join(map(str, [x for x in edge])) for edge in edges]
		return nodes_csv + edges_csv