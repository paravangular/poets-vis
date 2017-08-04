import sqlite3

import time

import json
import sys, os
from collections import defaultdict

from scripts.graph.core import *
from scripts.graph.events import *
from scripts.graph.load_xml import *
from scripts.graph_builder import *

class DBBuilder():
	def __init__(self, db_name, dir_name = "data/"):


		graph_src = dir_name + db_name + '.xml'
		event_src = dir_name + db_name + '_event.xml'

		if not os.path.exists(dir_name + "db/"):
			os.makedirs(directory + "db/")

		db_filename = dir_name + "db/" + db_name + ".db"

		if not os.path.isfile(db_filename):

			start_time = time.time()
			print("Creating database " + db_name + "...")
			self.graph = GraphBuilder(graph_src, event_src) # TODO: loading xml
			print
			print
			print("Partitioning...")
			self.metis = MetisHandler(self.graph, "data/metis/", 50)
			self.metis.execute_metis()

			print
			print("******************************************************************************")
			print("DATABASE CREATION")
			print("******************************************************************************")
			print("Creating database file " + db_name + ".db...")
			self.db = sqlite3.connect(db_filename)
			self.cursor = self.db.cursor()
			self.device_states()
			self.device_partitions()
			self.device_properties()
			self.edges()
			self.partition_edges()
			self.interpartition_edges()
			self.max_levels()

			for i in range(self.metis.nlevels - 1):
				self.aggregate_state_entries(level = i)
				self.aggregate_property_entries(level = i)
				self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_init ON device_states_aggregate_" + str(i) + " (init)")
				self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_parent ON device_states_aggregate_" + str(i) + " (parent)")
				self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_partition_id ON device_states_aggregate_" + str(i) + " (partition_id)")
				self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_aggregate_" + str(i) + "_epoch ON device_states_aggregate_" + str(i) + " (epoch)")
				self.db.execute("CREATE INDEX IF NOT EXISTS index_device_properties_" + str(i) + "_parent ON device_properties_aggregate_" + str(i) + " (parent)")
				self.db.execute("CREATE INDEX IF NOT EXISTS index_device_properties_" + str(i) + "_partition_id ON device_properties_aggregate_" + str(i) + " (partition_id)")

			print
			print("Database created.")
			self.db.close()
			print("******************************************************************************")
			print("FINISH (%3f seconds)" % (time.time() - start_time))
			print("******************************************************************************")

		else:
			print("Database already exists.")


	def close(self):
		self.db.close()

	def edges(self):
		fields = []
		fields.append(Field("source", "string", set(["key"])))
		fields.append(Field("target", "string", set(["key"])))
		fields.append(Field("source_port", "string"))
		fields.append(Field("target_port", "string"))
		fields.append(Field("message_type", "string"))

		self.create_table("edges", fields)

		values = []
		for id, edge in self.graph.raw.edge_instances.iteritems():
			values.append((edge.src_device.id, edge.dst_device.id, edge.src_port.name, edge.dst_port.name, edge.message_type.id))

		query = "INSERT INTO edges(source, target, source_port, target_port, message_type) VALUES(?, ?, ?, ?, ?)"
		self.db.executemany(query, values)

		print("  Creating indexes...")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_source ON edges (source)")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_target ON edges (target)")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_source_port ON edges (source_port)")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_target_port ON edges (target_port)")

	def interpartition_edges(self):
		fields = [Field("parent", "string", set("key")), Field("higher_level", "string", set("key")), Field("lower_level", "string", set("key")), Field("count", "int")]

		for i in range(self.metis.nlevels - 2, -1, -1):
			if i > 0:
				
				part = "partition_" + str(i)
				prev_part = "partition_" + str(i - 1)
				curr = self.metis.nlevels - i - 1
				prev = self.metis.nlevels - i
				self.create_table("interpartition_edges_{}_{}".format(curr, prev), fields)


				query = ("SELECT p1." + part + " AS higher_level, p2." + prev_part + " AS lower_level, COUNT(*) AS count" + 
					" FROM device_partitions AS p1 INNER JOIN edges ON edges.source = p1.id" + 
					" INNER JOIN device_partitions AS p2 ON edges.target = p2.id" + 
					" WHERE p1." + prev_part + " != p2." + prev_part + 
					" GROUP BY p1." + part + ", p2." + prev_part + 
					" UNION " + 
					" SELECT p3." + part + " AS higher_level, p4." + prev_part + " AS lower_level, COUNT(*) AS count" + 
					" FROM device_partitions AS p3 INNER JOIN edges ON edges.target = p3.id" + 
					" INNER JOIN device_partitions AS p4 ON edges.source = p4.id" + 
					" WHERE p3." + prev_part + " != p4." + prev_part + 
					" GROUP BY p3." + part + ", p4." + prev_part)

				insert_query = ("INSERT INTO interpartition_edges_{}_{}(higher_level, lower_level, count, parent) VALUES(?, ?, ?, ?)".format(curr, prev))

				cursor = self.db.cursor()
				cursor.execute(query)
				entries = []
				
				for row in cursor.fetchall():
					v = list(row)
					parent = "_".join(row[0].split("_")[:-1])
					v.append(parent)
					entries.append(tuple(v))
				cursor.close()
				self.db.executemany(insert_query, entries)

			else:
				curr = self.metis.nlevels - 1
				prev = self.metis.nlevels
				self.create_table("interpartition_edges_{}_{}".format(curr, prev), fields)
				part = "partition_" + str(self.metis.nlevels - 2)
				query = ("SELECT p1.id AS higher_level, p2." + part + " AS lower_level, COUNT(*) AS count, p1." + part + 
					" FROM device_partitions AS p1 INNER JOIN edges ON edges.source = p1.id" + 
					" INNER JOIN device_partitions AS p2 ON edges.target = p2.id" + 
					" WHERE p1." + part + " != p2." + part + 
					" GROUP BY p1.id , p2." + part + 
					" UNION " + 
					" SELECT p3.id AS higher_level, p4." + part + " AS lower_level, COUNT(*) AS count, p3." + part + 
					" FROM device_partitions AS p3 INNER JOIN edges ON edges.target = p3.id" + 
					" INNER JOIN device_partitions AS p4 ON edges.source = p4.id" + 
					" WHERE p3." + part + " != p4." + part + 
					" GROUP BY p3.id , p4." + part)

				insert_query = ("INSERT INTO interpartition_edges_{}_{}(higher_level, lower_level, count, parent) VALUES(?, ?, ?, ?)".format(curr, prev))

				cursor = self.db.cursor()
				cursor.execute(query)
				entries = []
				
				for row in cursor.fetchall():
					entries.append(tuple(row))
				cursor.close()
				self.db.executemany(insert_query, entries)

			
			print("  Creating indexes...")
			self.db.execute("CREATE INDEX IF NOT EXISTS index_interpartition_edges_{0}_{1}_parent ON interpartition_edges_{0}_{1} (parent)".format(curr, prev))
			self.db.execute("CREATE INDEX IF NOT EXISTS index_interpartition_edges_{0}_{1}_higher ON interpartition_edges_{0}_{1} (higher_level)".format(curr, prev))
			self.db.execute("CREATE INDEX IF NOT EXISTS index_interpartition_edges_{0}_{1}_lower ON interpartition_edges_{0}_{1} (lower_level)".format(curr, prev))


	def max_levels(self):
		self.create_table("levels", [Field("max", "int")])

		query = "INSERT INTO levels(max) VALUES(?)"
		value = [self.metis.nlevels]

		self.db.execute(query, value)

	def partition_edges(self):
		fields = [Field("parent", "string", set("key")), Field("source", "string", set("key")), Field("target", "string", set("key")), Field("count", "int")]
		for i in range(self.metis.nlevels):
			self.create_table("partition_edges_{}".format(i), fields)
			if i < self.metis.nlevels - 1:
				part = "partition_" + str(i)

				query = ("SELECT p1." + part + " AS source, p2." + part + " AS target, COUNT(*) AS count" + 
					" FROM device_partitions AS p1 INNER JOIN edges ON edges.source = p1.id" + 
					" INNER JOIN device_partitions AS p2 ON edges.target = p2.id" + 
					" WHERE p1.id != p2.id " + 
					" GROUP BY p1." + part + ", p2." + part)
				insert_query = ("INSERT INTO partition_edges_{}(source, target, count, parent) VALUES(?, ?, ?, ?)".format(i))
				cursor = self.db.cursor()
				cursor.execute(query)
				entries = []
				for row in cursor.fetchall():
					source_parent = "_".join(row[0].split("_")[:-1])
					target_parent = "_".join(row[1].split("_")[:-1])

					if source_parent == target_parent:
						v = list(row)
						v.append(source_parent)
						entries.append(tuple(v))

			else:
				part = "partition_" + str(i - 1)
				query = ("SELECT p1.id AS source, p2.id AS target, p1." + part + 
					" FROM device_partitions AS p1 INNER JOIN edges ON edges.source = p1.id" + 
					" INNER JOIN device_partitions AS p2 ON edges.target = p2.id" + 
					" WHERE p1." + part + " = p2." + part + 
					" AND p1.id != p2.id")

				cursor = self.db.cursor()
				cursor.execute(query)
				entries = []
				for row in cursor.fetchall():
					entries.append(tuple(row))

				insert_query = ("INSERT INTO partition_edges_{}(source, target, parent) VALUES(?, ?, ?)".format(i))
				ursor = self.db.cursor()
				cursor.execute(query)
				entries = []
				for row in cursor.fetchall():
					entries.append(tuple(row))

			cursor.close()
			self.db.executemany(insert_query, entries)
			print("  Creating indexes...")
			self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_edges_{0}_parent ON partition_edges_{0} (parent)".format(i))
			self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_edges_{0}_source ON partition_edges_{0} (source)".format(i))
			self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_edges_{0}_target ON partition_edges_{0} (target)".format(i))

	def device_partitions(self):
		query = "INSERT INTO device_partitions(id, "

		fields = []
		fields.append(Field("id", "string", set(["unique", "key"])))
		first = True
		for i in range(self.metis.nlevels - 1):
			fields.append(Field("partition_" + str(i), "int", set(["key", "not null"])))
			if not first:
				query += ", "
			query += "partition_" + str(i)
			first = False
			

		query += ") VALUES(?,"
		first = True
		for i in range(self.metis.nlevels - 1):
			if not first:
				query += ","
			query += "?"
			first = False

		query += ")"

		self.create_table("device_partitions", fields)

		entries = []
		for id, node in self.graph.nodes.iteritems():
			entry = [id]
			for i in range(self.metis.nlevels - 1):
				entry.append(node["partition_" + str(i)])

			entries.append(tuple(entry))

		self.db.executemany(query, entries)

		self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_id ON device_partitions (id)")
		for i in range(self.metis.nlevels - 1):
			self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_" + str(i) + " ON device_partitions (partition_" + str(i) + ")")

	def aggregate_state_entries(self, level, epoch = 5):
		aggregable_types = set(["INT", "int", "INTEGER", "integer", "REAL", "real"])
		aggregable_columns = []
		pragma_cursor = self.db.cursor()
		pragma_query = "PRAGMA table_info('device_states')"

		pragma_cursor.execute(pragma_query)

		query = "SELECT partition_" + str(level) + " AS partition_id, "
		first = True
		for row in pragma_cursor.fetchall():
			name = row[1]

			if name != "id" and name != "epoch" and name != "init":
				if row[2] in aggregable_types:
					if not first:
						query += ", "
					aggregable_columns.append(name)
					query += "AVG(" + name + ") AS " + name
					first = False

		
		
		#(SELECT s2.time FROM device_states AS s2 WHERE s2.time <=" + str(epoch) + " AND s2.id = s1.id ORDER BY s2.time DESC LIMIT 1)"
		pragma_cursor.close()

		cursor = self.db.cursor()

		print
		print("Aggregating states, level " + str(level) + " at init...")
		init_query = (" FROM device_states AS s1" + 
			" INNER JOIN device_partitions ON s1.id = device_partitions.id " + 
			" WHERE s1.epoch = 0 AND s1.init = 1" +
			" GROUP BY partition_" + str(level))
		print("  Executing query...")
		# print(query)
		
		cursor.execute(query + init_query)
		print("  Fetching results...")

		rows = cursor.fetchall()
		values = []
		for row in rows:
			parent = "_".join(row[0].split("_")[:-1])
			v = list(row) + [parent, 0, 1]
			values.append(tuple(v))
		
		print("  Inserting aggregates...")
		insert_query = ("INSERT INTO device_states_aggregate_" + str(level) +
						"(partition_id, " + ", ".join(aggregable_columns) + ", parent, epoch, init) VALUES(?, " + ", ".join(["?" for x in range(len(aggregable_columns))]) + ",?, ?, ?)")
		self.db.executemany(insert_query, values)
		self.db.commit()

		for i in range(epoch):
			print
			print("Aggregating states, level " + str(level) + " at epoch " + str(i) + "...")
			# select the latest event
			time_query = (" FROM device_states AS s1" + 
				" INNER JOIN device_partitions ON s1.id = device_partitions.id " + 
				" WHERE s1.epoch = " + 
				" (SELECT s2.epoch FROM device_states AS s2 WHERE s2.epoch <=" + str(i) + " AND s2.id = s1.id ORDER BY s2.epoch DESC LIMIT 1) "
				" GROUP BY partition_" + str(level))
			print("  Executing query...")
			# print(query)
			cursor.execute(query + time_query)

			print("  Fetching results...")
			rows = cursor.fetchall()
			values = []
			for row in rows:
				parent = "_".join(row[0].split("_")[:-1])
				v = list(row) + [parent, i, 0]
				values.append(tuple(v))
			
			print("  Inserting aggregates...")
			insert_query = ("INSERT INTO device_states_aggregate_" + str(level) +
							"(partition_id, " + ", ".join(aggregable_columns) + ", parent, epoch, init) VALUES(?, " + ", ".join(["?" for x in range(len(aggregable_columns))]) + ",?, ?, ?)")

			self.db.executemany(insert_query, values)
			self.db.commit()

	def aggregate_property_entries(self, level):
		aggregable_types = set(["INT", "int", "INTEGER", "integer", "REAL", "real"])
		aggregable_columns = []
		pragma_cursor = self.db.cursor()
		pragma_query = "PRAGMA table_info('device_properties')"

		pragma_cursor.execute(pragma_query)

		query = "SELECT partition_" + str(level) + " AS partition_id, "
		first = True
		for row in pragma_cursor.fetchall():
			name = row[1]

			if name != "id" and name != "type":
				if row[2] in aggregable_types:
					if not first:
						query += ", "
					aggregable_columns.append(name)
					if name == "messages_sent" or name == "messages_received":
						query += "SUM(" + name + ") AS " + name
					else:
						query += "AVG(" + name + ") AS " + name
					first = False

		query += (" FROM device_properties AS s1" + 
		" INNER JOIN device_partitions ON s1.id = device_partitions.id " + 
		" GROUP BY partition_" + str(level))
		
		pragma_cursor.close()

		cursor = self.db.cursor()
		print
		print("Aggregating properties, level " + str(level) + "...")
		print("  Executing query...")
		# print(query)
		cursor.execute(query)

		print("  Fetching results...")
		rows = cursor.fetchall()
		values = []
		for row in rows:
			parent = "_".join(row[0].split("_")[:-1])
			v = list(row)
			v.append(parent)
			values.append(tuple(v))
		
		print("  Inserting aggregates...")
		insert_query = ("INSERT INTO device_properties_aggregate_" + str(level) +
						"(partition_id, " + ", ".join(aggregable_columns) + ", parent) VALUES(?, " + ", ".join(["?" for x in range(len(aggregable_columns))]) + ", ?)")

		self.db.executemany(insert_query, values)
		self.db.commit()

	def device_properties(self):
		fields = []
		fields.append(Field("id", "string", set(["unique", "key"])))
		fields.append(Field("type", "string", set(["not null"])))
		fields.append(Field("messages_sent", "int", set(["not null"])))
		fields.append(Field("messages_received", "int", set(["not null"])))

		types = self.graph.raw.graph_type.device_types
		cols = {}
		for id, dev_type in types.iteritems():
			for prop in dev_type.properties.elements_by_index:
				if prop.name not in cols:
					if not isinstance(prop, ArrayTypedDataSpec): 
						fields.append(Field(prop.name, prop.type))
						cols[prop.name] = None
					else: 
						fields.append(Field(prop.name, "array"))


		self.create_table("device_properties", fields)
		values = []
		for id, dev in self.graph.raw.device_instances.iteritems():
			v = {"id": id, "type": dev.device_type.id, "messages_sent": self.graph.nodes[id]["messages_sent"], "messages_received": self.graph.nodes[id]["messages_received"]}
			p = dev.properties.copy()
			c = cols.copy()
			v.update(p)
			c.update(v)
			values.append(c)

		self.insert_rows("device_properties", fields, values)

		print("  Creating indexes...")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_properties_id ON device_properties(id)")

		fields[0] = Field("parent", "int", set(["key"]))
		fields[1] = Field("partition_id", "int", set(["unique", "key"]))
		for i in range(self.metis.nlevels - 1):
			self.create_table("device_properties_aggregate_" + str(i), fields)

	def device_states(self):
		fields = []
		fields.append(Field("id", "string", set(["unique", "key", "not null"])))
		fields.append(Field("epoch", "integer", set(["unique", "key", "not null"])))
		fields.append(Field("init", "integer", set(["not null", "key"])))

		types = self.graph.raw.graph_type.device_types
		cols = set()
		for id, dev_type in types.iteritems():
			for state in dev_type.state.elements_by_index:
				if state.name not in cols:
					if not isinstance(state, ArrayTypedDataSpec): 
						fields.append(Field(state.name, state.type))
						cols.add(state.name)
					else: 
						fields.append(Field(state.name, "array"))

		self.create_table("device_states", fields)
		values = []

		for id, evt in self.graph.events["init"].iteritems():
			values.append(self.build_state_values(evt, cols))

		for id, evt in self.graph.events["msg"].iteritems():
			values.append(self.build_state_values(evt, cols))
		
		self.insert_rows("device_states", fields, values)

		print("  Creating indexes...")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_id ON device_states (id)")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_init ON device_states (init)")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_time ON device_states (epoch)")

		fields.append(Field("parent", "int", set(["key"])))
		fields[0] = Field("partition_id", "int")
		for i in range(self.metis.nlevels - 1):
			self.create_table("device_states_aggregate_" + str(i), fields)

	
	def build_state_values(self, evt, col = None):
		value = defaultdict(lambda:None, evt.S)
		value["id"] = evt.dev
		value["epoch"] = evt.time

		if evt.type == "init":
			value["init"] = 1
		else:
			value["init"] = 0

		for k, v in value.iteritems():
			if isinstance(v, list):
				value[k] = str(v)

		if col:
			if len(value) != len(col):
				for i in col:
					if i not in value:
						value[i] = None

		return value

	def insert_rows(self, table_name, fields, values):
		colnames = map(str, fields)
		columns = ",".join(colnames)
		placeholders = ":" + ",:".join(colnames)
		query = "INSERT INTO " + table_name + "(%s) VALUES (%s)" % (columns, placeholders)
		
		self.db.executemany(query, values)
		self.db.commit()

	def create_table(self, table_name, fields):
		print
		print("Creating table " + table_name + "...")
		query = "CREATE TABLE IF NOT EXISTS " + table_name + "("
		first = True

		keys = []
		unique = []
		for f in fields:
			if "key" in f.properties:
				key.append(f.name)

			if "unique" in f.properties:
				unique.append(f.name)

			if not first:
				query += ", "
			query += f.get()
			first = False

		if keys:
			query += ", PRIMARY KEY (" + ",".join(keys) + ")"

		if unique:
			query += ", UNIQUE (" + ",".join(unique) + ") ON CONFLICT DO NOTHING"
 
		query += ")"
		self.db.execute(query)

		self.db.commit()


class Field():
	def __init__(self, name, data_type, properties = None):
		self.name = name
		self.type = self.parse_type(data_type)
		self.properties = self.parse_properties(properties)

	def __str__(self):
		return self.name

	def get(self):
		return self.name + " " + self.type + self.properties

	def parse_properties(self, prop):
		if prop is None:
			return ""

		res = []
		if "key" in prop:
			res.append("NOT NULL")
		if "not null" in prop:
			res.append("NOT NULL")

		return " " + " ".join(res)


	def parse_type(self, data_type):
		if data_type == "float":
			return "REAL"
		elif "int" in data_type:
			return "INTEGER"
		elif data_type == "string":
			return "TEXT"
		else:
			return "BLOB"



