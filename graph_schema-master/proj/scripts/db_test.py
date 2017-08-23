import unittest
import os
import sys
sys.path.append('../proj')
from db_builder import *

class TestDB(unittest.TestCase):
	def setUp(self):
		self.db = DBBuilder("test")
		self.graph_type = {"id": "test", 
							"device_types": {"devtype1": {"properties": set([("devprop1", "int"), ("devprop2", "string")]), 
														"state": set([("devstate1", "int"), ("devstate2", "string")]), 
														"ports": {"input": {"inport1": {"name": "inport1", "message_type": "msg1"}}, 
																"output": {"outport1": {"name": "outport1", "message_type": "msg1"}}
																}}}}
		self.curr_graph = {"device_instances": {"dev1": {"id": "dev1", "type": "devtype1", "properties": {"devprop1": 1, "devprop2": "1"}},
												"dev2": {"id": "dev2", "type": "devtype1", "properties": {"devprop1": 2, "devprop2": "2"}}}, 
												"edge_instances": [{"source": "dev1", "target": "dev2", "source_port": "outport1", "target_port": "inport1"},
																	{"source": "dev2", "target": "dev1", "source_port": "outport1", "target_port": "inport1"}]}

	def test_db_creation(self):
		self.assertTrue(os.path.isfile("data/db/test.db"))
		self.assertEquals(self.db.event_src, "data/test_event.xml")
		self.assertEquals(self.db.granularity, 0)
		self.assertEquals(self.db.max_epoch, 0)

		print(self.db.db)

	def test_create_table(self):
		fields = [Field("test_field", "int")]
		self.db.create_table("test_table", fields)

		cursor = self.db.db.cursor()
		cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'");

		row = cursor.fetchall()
		self.assertEquals(len(row), 1)
		cursor = self.db.db.cursor()
		cursor.execute( "PRAGMA table_info('test_table')")
		field_rows = cursor.fetchall()
		self.assertEquals(len(field_rows), 1)
		self.assertEquals(field_rows[0][1], "test_field")

	def test_insert_rows(self):
		fields = [Field("test_field", "int")]
		self.db.create_table("test_table", fields)
		values = [(1,), (2, )]
		self.db.insert_rows("test_table", fields, values)

		cursor = self.db.db.cursor()
		cursor.execute("SELECT * FROM 'test_table'")
		self.assertEquals(len(cursor.fetchall()), 2)

	def test_device_types(self):
		self.db.device_types(self.graph_type)
		cursor = self.db.db.cursor()
		cursor.execute( "PRAGMA table_info('device_types')")
		rows = cursor.fetchall()
		self.assertEquals(rows[0][1], "id")
		self.assertEquals(rows[1][1], "states")
		self.assertEquals(rows[2][1], "properties")

		cursor = self.db.db.cursor()
		cursor.execute("SELECT * FROM 'device_types'")
		rows = cursor.fetchall()
		self.assertEquals(rows[0][0], "devtype1")
		self.assertTrue(rows[0][1] == "devstate1,devstate2" or rows[0][1] == "devstate2,devstate1")
		self.assertTrue(rows[0][2] == "devprop1,devprop2" or rows[0][1] == "devprop2,devprop1")

	def test_edges(self):
		self.db.edges(self.curr_graph["edge_instances"])

		cursor = self.db.db.cursor()
		cursor.execute("SELECT * FROM 'edges'")
		rows = cursor.fetchall()
		self.assertTrue(rows[0][0] == "dev1")
		self.assertTrue(rows[0][1] == "dev2")
		self.assertTrue(rows[0][2] == "outport1")
		self.assertTrue(rows[0][3] == "inport1")
		self.assertTrue(rows[1][0] == "dev2")
		self.assertTrue(rows[1][1] == "dev1")
		self.assertTrue(rows[1][2] == "outport1")
		self.assertTrue(rows[1][3] == "inport1")

	def tearDown(self):
		os.remove("data/db/test.db")

if __name__ == '__main__':
	unittest.main(verbosity = 2, buffer = True)