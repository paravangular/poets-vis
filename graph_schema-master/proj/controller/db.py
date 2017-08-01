import sqlite3

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
		metis = MetisHandler(self.graph, "../data/metis/", 50)
		metis.execute_metis()

		self.db = sqlite3.connect(self.graph.raw.graph_type.id + '.db')
		self.cursor = self.db.cursor()
		self.devices()
		self.device_states()
		self.device_partitions()
		self.device_properties()

	def close(self):
		self.db.close()

	def device_partitions(self):
		query = "INSERT INTO device_partitions(id, "

		fields = []
		fields.append(Field("id", "string", set(["key"])))
		first = True
		for i in range(self.graph.levels):
			fields.append(Field("partition_" + str(i), "int", set(["not null"])))
			if not first:
				query += ", "
			query += "partition_" + str(i)
			first = False

		query += ") VALUES(?,"
		first = True
		for i in range(self.graph.levels):
			if not first:
				query += ","
			query += "?"
			first = False

		query += ")"

		self.create_table("device_partitions", fields)

		entries = []
		for id, node in self.graph.nodes.iteritems():
			entry = [id]
			for i in range(self.graph.levels):
				entry.append(node["partition_" + str(i)])

			entries.append(tuple(entry))

		# self.cursor.executemany(query, entries)

	def aggregate_state_entries(self, level, epoch = 0):

		aggregable_types = set(["INT", "int", "INTEGER", "integer", "REAL", "real"])
		aggregable_columns = []
		pragma_cursor = self.db.cursor()
		pragma_query = "PRAGMA table_info('device_states')"

		pragma_cursor.execute(pragma_query)

		query = "SELECT partition_" + str(level) + " AS partition_id, "
		first = True
		for row in pragma_cursor.fetchall():
			if not first:
				query += ", "
			name = row[1]

			if name != "id" or name != "time":
				if row[2] in aggregable_types:
					aggregable_columns.append(name)
					query += "AVG(" + name + ") AS " + name
					first = False

		query += (" FROM (SELECT * FROM device_states WHERE time <= " + epoch + ") AS states" + 
			" JOIN (SELECT id, MAX(time) AS time FROM device_states WHERE time <= " + epoch + " GROUP BY id) AS last_event ON states.id = last_event.id AND states.time = last_event.time"  
			" JOIN device_partitions ON states.id = device_partitions.id " + 
			" GROUP BY partition_" + str(level) +
			" ORDER BY partition_" + str(level))
		

		pragma_cursor.close()

		cursor = self.db.cursor()
		cursor.execute(query)
		rows = cursor.fetchall()
		values = []
		for row in rows:
			values.append(tuple([col in row]))
		

		insert_query = ("INSERT INTO device_states_aggregate_" + str(level) +
						"(partition_id, " + ", ".join(aggregable_columns) + ") VALUES(?, " + ", ".join(["?" for x in range(len(aggregable_columns))]))

		insert_cursor = self.db.cursor()
		insert_cursor.executemany(insert_query, values)
		insert_cursor.close()
		self.db.commit()


		'''
		group rows by partition_number
		fetch average per partition where time is the maximum time smaller than epoch

		'''

	# def part_aggregates(self, level, epoch = 0):
	# 	n = self.metis.num_parts

	# 	self.cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='device_states'")
	# 	sql = self.cursor.fetchone() # this will give the "CREATE TABLE device_states(...)"
	# 	columns = sql[sql.index("(") + 1:sql.rindex(")")]

	# 	query = "CREATE TABLE " + 

	def devices(self):
		fields = []
		fields.append(Field("id", "string", set(["key"])))
		fields.append(Field("type", "int", set(["not null"])))

		self.create_table("devices", fields)

	def device_properties(self):
		fields = []
		fields.append(Field("id", "string", set(["key"])))
		fields.append(Field("messages_sent", "int", set(["not null"])))
		fields.append(Field("messages_received", "int", set(["not null"])))

		types = self.graph.raw.graph_type.device_types
		for id, dev_type in types.iteritems():
			for prop in dev_type.properties.elements_by_index:
				fields.append(Field(prop.name, prop.type))

		fields[0] = Field("partition_id", "int", set(["key"]))
		self.create_table("device_properties", fields)
		for i in range(self.graph.levels):
			self.create_table("device_properties_aggregate_" + str(i), fields)

	def device_states(self):
		fields = []
		fields.append(Field("id", "string"))
		fields.append(Field("time", "integer", set(["not null"])))

		types = self.graph.raw.graph_type.device_types
		for id, dev_type in types.iteritems():
			for state in dev_type.state.elements_by_index:
				if not isinstance(state, ArrayTypedDataSpec): 
					fields.append(Field(state.name, state.type))
				else: 
					fields.append(Field(state.name, "array"))

		self.create_table("device_states", fields)

		fields[0] = Field("partition_id", "int")
		for i in range(self.graph.levels):
			self.create_table("device_states_aggregate_" + str(i), fields)

	def create_table(self, table_name, fields):
		query = "CREATE TABLE IF NOT EXISTS " + table_name + "("
		first = True
		for f in fields:
			if not first:
				query += ", "
			query += f.get()
			first = False

		query += ")"
		self.db.execute(query)
		self.db.commit()


class Field():
	def __init__(self, name, data_type, properties = None):
		self.name = name
		self.type = self.parse_type(data_type)
		self.properties = self.parse_properties(properties)

	def get(self):
		return self.name + " " + self.type + self.properties

	def parse_properties(self, prop):
		if prop is None:
			return ""

		res = []
		if "key" in prop:
			res.append("PRIMARY KEY")
		
		if "unique" in prop:
			res.append("UNIQUE")

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


local_file = 'ising_spin_100x100'
db = DBBuilder('../data/' + local_file + '.xml', '../data/' + local_file + '_event.xml')
db.close()
