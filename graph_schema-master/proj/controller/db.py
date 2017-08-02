import sqlite3

import time

import xml.sax
import json
import sys, os
from collections import defaultdict

import xml.etree.ElementTree as ET
from lxml import etree

# from controller.graph.core import *
# from controller.graph.events import *
# from controller.graph.load_xml import *
from graph.core import *
from graph.events import *
from graph.load_xml import *
from graph_builder import *

'''
SCHEMA

device_partitions
devices
	- device id
	- type
	- messages_sent
	- messages_received
device_properties
	- properties (for every device)
device_states: device state at every change
	- id
	- time
	- states


'''

class DBBuilder():
	def __init__(self, graph_src, event_src):
		
		self.graph = GraphBuilder(graph_src, event_src)
		db_filename = "../data/db/" + self.graph.raw.id + ".db"

		if not os.path.isfile(db_filename):
			self.metis = MetisHandler(self.graph, "../data/metis/", 50)
			self.metis.execute_metis()

			self.db = sqlite3.connect(db_filename)
			self.cursor = self.db.cursor()
			self.devices()
			self.device_states()
			self.device_partitions()
			self.device_properties()
			for i in range(self.metis.nlevels - 1):
				self.aggregate_state_entries(level = i)
				self.db.execute("CREATE INDEX IF NOT EXISTS index_states_" + str(i) + "_partition_id ON device_states_aggregate_" + str(i) + " (partition_id)")

			db.close()

		else:
			print("Database already exists.")


	def close(self):
		self.db.close()

	def device_partitions(self):
		query = "INSERT INTO device_partitions(id, "

		fields = []
		fields.append(Field("id", "string", set(["unique", "key"])))
		first = True
		for i in range(self.metis.nlevels - 1):
			fields.append(Field("partition_" + str(i), "int", set(["not null"])))
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

		for i in range(self.metis.nlevels - 1):
			self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_" + str(i) + " ON device_partitions (partition_" + str(i) + ")")

	def aggregate_state_entries(self, level, epoch = 0):
		aggregable_types = set(["INT", "int", "INTEGER", "integer", "REAL", "real"])
		aggregable_columns = []
		pragma_cursor = self.db.cursor()
		pragma_query = "PRAGMA table_info('device_states')"

		pragma_cursor.execute(pragma_query)

		query = "SELECT partition_" + str(level) + " AS partition_id, "
		first = True
		for row in pragma_cursor.fetchall():
			name = row[1]

			if name != "id" or name != "time":
				if row[2] in aggregable_types:
					if not first:
						query += ", "
					aggregable_columns.append(name)
					query += "AVG(" + name + ") AS " + name
					first = False

		# select the latest event
		query += (" FROM device_states AS s1" + 
		" INNER JOIN device_partitions ON s1.id = device_partitions.id " + 
		" WHERE s1.time = " + 
		" (SELECT s2.time FROM device_states AS s2 WHERE s2.time <=" + str(epoch) + " AND s2.id = s1.id ORDER BY s2.time DESC LIMIT 1) "
		" GROUP BY partition_" + str(level))
		
		#(SELECT s2.time FROM device_states AS s2 WHERE s2.time <=" + str(epoch) + " AND s2.id = s1.id ORDER BY s2.time DESC LIMIT 1)"
		pragma_cursor.close()

		cursor = self.db.cursor()
		print("Executing query...")
		print(query)
		cursor.execute(query)

		print("Fetching results...")
		rows = cursor.fetchall()
		values = []
		for row in rows:
			v = list(row) + [epoch]
			values.append(v)
		
		print("Inserting aggregates...")
		insert_query = ("INSERT INTO device_states_aggregate_" + str(level) +
						"(partition_id, " + ", ".join(aggregable_columns) + ", time) VALUES(?, " + ", ".join(["?" for x in range(len(aggregable_columns))]) + ",?)")

		self.db.executemany(insert_query, values)
		self.db.commit()


		'''
		group rows by partition_number
		fetch average per partition where time is the maximum time smaller than epoch

		'''

	def devices(self):
		fields = []
		fields.append(Field("id", "string", set(["unique", "key"])))
		fields.append(Field("type", "int", set(["not null"])))

		self.create_table("devices", fields)

	def device_properties(self):
		fields = []
		fields.append(Field("id", "string", set(["unique", "key"])))
		fields.append(Field("messages_sent", "int", set(["not null"])))
		fields.append(Field("messages_received", "int", set(["not null"])))

		types = self.graph.raw.graph_type.device_types
		for id, dev_type in types.iteritems():
			for prop in dev_type.properties.elements_by_index:
				fields.append(Field(prop.name, prop.type))

		fields[0] = Field("partition_id", "int", set(["unique", "key"]))
		self.create_table("device_properties", fields)
		for i in range(self.metis.nlevels - 1):
			self.create_table("device_properties_aggregate_" + str(i), fields)

	def device_states(self):
		fields = []
		fields.append(Field("id", "string", set(["unique", "key", "not null"])))
		fields.append(Field("time", "integer", set(["unique", "key", "not null"])))

		types = self.graph.raw.graph_type.device_types
		for id, dev_type in types.iteritems():
			for state in dev_type.state.elements_by_index:
				if not isinstance(state, ArrayTypedDataSpec): 
					fields.append(Field(state.name, state.type))
				else: 
					fields.append(Field(state.name, "array"))

		self.create_table("device_states", fields)
		values = []

		for id, evt in self.graph.events.iteritems():
			values.append(self.build_values(evt))
		self.insert_rows("device_states", fields, values)

		self.db.execute("CREATE INDEX IF NOT EXISTS index_states_id ON device_states (id)")
		self.db.execute("CREATE INDEX IF NOT EXISTS index_states_time ON device_states (time)")

		fields[0] = Field("partition_id", "int")
		for i in range(self.metis.nlevels - 1):
			self.create_table("device_states_aggregate_" + str(i), fields)

	
	def build_values(self, evt):
		value = defaultdict(lambda:None, evt.S)
		value["id"] = evt.dev
		value["time"] = evt.time
		
		for k, v in value.iteritems():
			if isinstance(v, list):
				value[k] = str(v)

		return value

	def insert_rows(self, table_name, fields, values):
		colnames = map(str, fields)
		columns = ",".join(colnames)
		placeholders = ":" + ",:".join(colnames)
		query = "INSERT INTO " + table_name + "(%s) VALUES (%s)" % (columns, placeholders)
		
		self.db.executemany(query, values)
		self.db.commit()

	def create_table(self, table_name, fields):

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


start_time = time.time()

local_file = 'ising_spin_100x100'
db = DBBuilder('../data/' + local_file + '.xml', '../data/' + local_file + '_event.xml')

print("--- %s seconds ---" % (time.time() - start_time))
