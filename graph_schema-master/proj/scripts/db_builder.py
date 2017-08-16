import sqlite3

import time
import math

import json
import sys, os
from collections import defaultdict

from scripts.graph.core import *
from scripts.graph.events import *
from scripts.graph.load_xml_stream import *
from scripts.graph_builder import *
import xml.etree.cElementTree as ET
from lxml import etree

class Handler():
    def __init__(self, db_name, base_dir = "data/"):
        src = base_dir + db_name + '.xml'
        event_src = base_dir + db_name + '_event.xml'

        self.dbb = DBBuilder(db_name, base_dir)
        graph_type, curr_graph, graph_props = load_graph_type_and_instances(src, self.dbb)
        self.dbb.graph_properties(graph_type)
        self.dbb.device_types(graph_type)
        self.dbb.device_states(graph_type)
        self.dbb.ranges_init(graph_type)



        self.dbb.device_properties(graph_type, curr_graph["device_instances"])
        self.dbb.edges(curr_graph["edge_instances"])

        # self.dbb.insert_rows("graph_properties", graph_props)
        

        simple_graph = GraphBuilder(curr_graph)
        metis = MetisHandler(db_name, simple_graph)
        metis.execute_metis()

        self.dbb.device_partitions(simple_graph, metis.nlevels)
        self.dbb.partition_edges(metis.nlevels)
        self.dbb.interpartition_edges(metis.nlevels)
        self.dbb.meta_properties(metis.nlevels)

        self.dbb.events()
        self.dbb.aggregates(graph_type, metis.nlevels)
        self.dbb.load_ranges()
        self.dbb.db.close()


class DBBuilder():
    def __init__(self, db_name, dir_name = "data/", max_time = 100, max_events = 1000000, max_epoch_intervals = 10):

        graph_src = dir_name + db_name + '.xml'
        self.event_src = dir_name + db_name + '_event.xml'
        self.snap_src = dir_name + db_name + '_snapshot.xml'
        self.max_events = max_events
        self.max_epoch_intervals = max_epoch_intervals
        self.snapshots = set()
        self.max_time = max_time


        self.message_counts = {"send": defaultdict(int), "recv": defaultdict(int)}
        
        if not os.path.exists(dir_name + "db/"):
            os.makedirs(directory + "db/")

        db_filename = dir_name + "db/" + db_name + ".db"
        self.db = sqlite3.connect(db_filename)

        # if not os.path.isfile(db_filename):

        #     start_time = time.time()
        #     print("Creating database " + db_name + "...")
        #     self.graph = GraphBuilder(graph_src, event_src)

        #     if int(math.ceil(self.graph.max_time)) > self.max_epoch_intervals:
        #         self.snapshot_interval = int(math.ceil(self.graph.max_time / self.max_epoch_intervals))
        #     else:
        #         self.snapshot_interval = 1

        #     print
        #     print
        #     print("Partitioning...")
        #     self.metis = MetisHandler(self.graph, "data/metis/", 50)
        #     self.metis.execute_metis()

        #     print
        #     print("******************************************************************************")
        #     print("DATABASE CREATION")
        #     print("******************************************************************************")
        #     print("Creating database file " + db_name + ".db...")
        #     self.db = sqlite3.connect(db_filename)
        #     self.cursor = self.db.cursor()
        #     self.device_types()
        #     self.device_states()
        #     self.device_partitions()
        #     self.device_properties()
        #     self.edges()
        #     



        #     print
        #     print("Database created.")
        #     self.db.close()
        #     print("******************************************************************************")
        #     print("FINISH (%3f seconds)" % (time.time() - start_time))
        #     print("******************************************************************************")

        # else:
        #     print("Database already exists.")

    def aggregates(self, graph_type, level):
        for i in range(level - 1):
            self.create_table("device_states_aggregate_" + str(i), self.aggregate_states_fields(self.device_states_fields(graph_type)[1]))
            self.aggregate_state_entries(level = i)
            self.create_table("device_properties_aggregate_" + str(i), self.aggregate_properties_fields(self.device_properties_fields(graph_type)[1]))

            self.aggregate_property_entries(level = i)

            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_init ON device_states_aggregate_" + str(i) + " (init)")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_parent ON device_states_aggregate_" + str(i) + " (parent)")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_init_parent ON device_states_aggregate_" + str(i) + " (init, parent)")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_epoch_parent ON device_states_aggregate_" + str(i) + " (epoch, parent)")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_" + str(i) + "_partition_id ON device_states_aggregate_" + str(i) + " (partition_id)")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_aggregate_" + str(i) + "_epoch ON device_states_aggregate_" + str(i) + " (epoch)")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_properties_" + str(i) + "_parent ON device_properties_aggregate_" + str(i) + " (parent)")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_device_properties_" + str(i) + "_partition_id ON device_properties_aggregate_" + str(i) + " (partition_id)")

    def graph_properties(self, graph_type):
        fields = []
        fields.append(Field("id", "string", set(["key", "not null", "unique"])))

        for prop in graph_type["properties"]:
            fields.append(Field(prop[0], prop[1]))

        self.create_table("graph_properties", fields)

    def device_types(self, graph_type):
        fields = []
        fields.append(Field("id", "string", set(["key", "not null", "unique"])))
        fields.append(Field("states", "string"))
        fields.append(Field("properties", "string"))

        self.create_table("device_types", fields)
        values = []
        for id, dev in graph_type["device_types"].iteritems():
            state = ""
            for s in dev["state"]:
                if s[1][0] != "[" and s[0][-1] != "]":
                    state += s[0] + ","
                else:
                    state += "[" + s[0] + "],"

            properties = ""
            for p in dev["properties"]:
                if p[1][0] != "[" and p[0][-1] != "]":
                    properties += p[0] + ","
                else:
                    properties += "[" + p[0] + "],"

            values.append((id, state[:-1], properties[:-1]))
        self.insert_rows("device_types", fields, values)

    def edges(self, edge_instances):
        fields = []
        fields.append(Field("source", "string", set(["key"])))
        fields.append(Field("target", "string", set(["key"])))
        fields.append(Field("source_port", "string"))
        fields.append(Field("target_port", "string"))

        self.create_table("edges", fields)

        values = []
        for edge in edge_instances:
            values.append((edge["source"], edge["target"], edge["source_port"], edge["target_port"]))

        query = "INSERT INTO edges(source, target, source_port, target_port) VALUES(?, ?, ?, ?)"
        self.db.executemany(query, values)

        print("  Creating indexes...")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_source ON edges (source)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_target ON edges (target)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_source_port ON edges (source_port)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_edges_target_port ON edges (target_port)")

    def interpartition_edges(self, level):
        fields = [Field("parent", "string", set("key")), Field("higher_level", "string", set("key")), Field("lower_level", "string", set("key")), Field("count", "int")]

        for i in range(level - 2, -1, -1):
            if i > 0:
                
                part = "partition_" + str(i)
                prev_part = "partition_" + str(i - 1)
                curr = level - i - 1
                prev = level - i
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
                cursor.arraysize = 10000
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
                curr = level - 1
                prev = level
                self.create_table("interpartition_edges_{}_{}".format(curr, prev), fields)
                part = "partition_" + str(level - 2)
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
                cursor.arraysize = 10000
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

    def meta_properties(self, level):
        fields = [Field("name", "string", set(["key", "not null", "unique"])), Field("max", "int")]
        self.create_table("meta_properties", fields)
        query = "INSERT INTO meta_properties(name, max) VALUES(?, ?)"
        values = [{"name": "level", "max": level}, {"name": "time", "max": int(math.ceil(self.max_time))}]
        
        self.insert_rows("meta_properties", fields, values)

    def partition_edges(self, level):
        fields = [Field("parent", "string", set("key")), Field("source", "string", set("key")), Field("target", "string", set("key")), Field("count", "int")]
        for i in range(level):
            self.create_table("partition_edges_{}".format(i), fields)
            if i < level - 1:
                part = "partition_" + str(i)

                query = ("SELECT p1." + part + " AS source, p2." + part + " AS target, COUNT(*) AS count" + 
                    " FROM device_partitions AS p1 INNER JOIN edges ON edges.source = p1.id" + 
                    " INNER JOIN device_partitions AS p2 ON edges.target = p2.id" + 
                    " WHERE p1.id != p2.id " + 
                    " GROUP BY p1." + part + ", p2." + part)
                insert_query = ("INSERT INTO partition_edges_{}(source, target, count, parent) VALUES(?, ?, ?, ?)".format(i))
                cursor = self.db.cursor()
                cursor.arraysize = 10000
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
                cursor.arraysize = 10000
                cursor.execute(query)
                entries = []
                for row in cursor.fetchall():
                    entries.append(tuple(row))

                insert_query = ("INSERT INTO partition_edges_{}(source, target, parent) VALUES(?, ?, ?)".format(i))
                cursor = self.db.cursor()
                cursor.arraysize = 10000
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

    def device_partitions(self, simple_graph, part_levels):
        query = "INSERT INTO device_partitions(id, "

        fields = []
        fields.append(Field("id", "string", set(["unique", "key"])))
        first = True
        for i in range(part_levels - 1):
            fields.append(Field("partition_" + str(i), "int", set(["key", "not null"])))
            if not first:
                query += ", "
            query += "partition_" + str(i)
            first = False
            

        query += ") VALUES(?,"
        first = True
        for i in range(part_levels - 1):
            if not first:
                query += ","
            query += "?"
            first = False

        query += ")"

        self.create_table("device_partitions", fields)

        entries = []
        for id, node in simple_graph.nodes.iteritems():
            entry = [id]
            for i in range(part_levels - 1):
                entry.append(node["partition_" + str(i)])

            entries.append(tuple(entry))

        self.db.executemany(query, entries)

        self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_id ON device_partitions (id)")
        for i in range(part_levels - 1):
            self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_" + str(i) + " ON device_partitions (partition_" + str(i) + ")")
            self.db.execute("CREATE INDEX IF NOT EXISTS index_partition_id_dev_id ON device_partitions (id, partition_" + str(i) + ")")

    def aggregate_state_entries(self, level):

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
        cursor.arraysize = 10000

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

        for i in self.snapshots:
            print
            if i != "init":
                print("Aggregating states, level " + str(level) + " at epoch " + i + "...")
                # select the latest event
                time_query = (" FROM device_states AS s1" + 
                    " INNER JOIN device_partitions ON s1.id = device_partitions.id " + 
                    " WHERE s1.epoch = " + i + 
                    " GROUP BY partition_" + str(level))
                print("  Executing query...")
                # print(query)
                cursor.execute(query + time_query)
                cursor.arraysize = 10000

                print("  Fetching results...")
                rows = cursor.fetchall()
                values = []
                for row in rows:
                    parent = "_".join(row[0].split("_")[:-1])
                    v = list(row) + [parent, i, 0]
                    values.append(tuple(v))
                
                print("  Inserting {} records to device_states_aggregate_{}...".format(len(values), level))
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
        cursor.arraysize = 10000
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
        
        print("  Inserting {} records to device_properties_aggregate_{}...".format(len(values), level))
        insert_query = ("INSERT INTO device_properties_aggregate_" + str(level) +
                        "(partition_id, " + ", ".join(aggregable_columns) + ", parent) VALUES(?, " + ", ".join(["?" for x in range(len(aggregable_columns))]) + ", ?)")

        self.db.executemany(insert_query, values)
        self.db.commit()

    def device_properties_fields(self, graph_type):
        fields = []
        fields.append(Field("id", "string", set(["key", "not null", "unique"])))
        fields.append(Field("type", "string", set(["key", "not null"])))

        cols = {}
        for id, dev in graph_type["device_types"].iteritems():
            for prop in dev["properties"]:
                if prop[0] not in cols:
                    if prop[1][0] != "[" and prop[0][-1] != "]":
                        fields.append(Field(prop[0], prop[1]))
                        cols[prop[0]] = None
                    else:
                        fields.append(Field(prop[0], "array"))

        return (cols, fields)

    def aggregate_properties_fields(self, fields):
        fields[0] = Field("parent", "int", set(["key"]))
        fields[1] = Field("partition_id", "int", set(["unique", "key"]))

        return fields

    def device_states_fields(self, graph_type):
        fields = []
        fields.append(Field("id", "string", set(["key", "not null", "unique"])))
        fields.append(Field("epoch", "integer"))
        fields.append(Field("init", "integer", set(["not null", "key"])))

        cols = {}
        for id, dev in graph_type["device_types"].iteritems():
            for prop in dev["state"]:
                if prop[0] not in cols:
                    if prop[1][0] != "[" and prop[0][-1] != "]":
                        fields.append(Field(prop[0], prop[1]))
                        cols[prop[0]] = None
                    else:
                        fields.append(Field(prop[0], "array"))

        return (cols, fields)

    def device_properties(self, graph_type, device_instances):
        cols, fields = self.device_properties_fields(graph_type)
        # fields.append(Field("messages_sent", "int", set(["not null"])))
        # fields.append(Field("messages_received", "int", set(["not null"])))

        types = graph_type["device_types"]

        # self.ranges["messages_sent"] = [0, float("-inf")]
        # self.ranges["messages_received"] = [0, float("-inf")]

        self.create_table("device_properties", fields)
        values = []
        for id, dev in device_instances.iteritems():
            v = {"id": id, "type": dev["type"]}
            p = dev["properties"].copy()
            c = cols.copy()
            v.update(p)
            c.update(v)
            values.append(c)

            # self.ranges["messages_sent"][1] = max(self.ranges["messages_sent"][1], v["messages_sent"])
            # self.ranges["messages_received"][1] = max(self.ranges["messages_received"][1], v["messages_received"])

        self.insert_rows("device_properties", fields, values)

        print("  Creating indexes...")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_properties_id ON device_properties(id)")

    def range_fields(self):
        return [Field("state", "string", set(["unique", "key", "not null"])), Field("min", "float"), Field("max", "float")]

    def events_fields(self):
        fields = []
        fields.append(Field("id", "string", set(["unique", "key", "not null"])))
        fields.append(Field("dev", "string", set(["key", "not null"])))
        fields.append(Field("type", "string", set(["not null"])))
        fields.append(Field("time", "float", set(["key", "not null"])))
        fields.append(Field("elapsed", "float",set(["not null"])))
        fields.append(Field("rts", "string", set(["not null"])))
        fields.append(Field("seq", "integer", set(["not null"])))
        fields.append(Field("port", "string"))
        fields.append(Field("send_id", "string"))
        fields.append(Field("cancel", "string"))
        fields.append(Field("fanout", "string"))
        fields.append(Field("m", "string"))
        fields.append(Field("s", "string"))

        self.create_table("events", fields)
        return fields

    def events(self, max_events = 10000000, batch = 100000):

        values = []
        fields = self.events_fields()

        print("  Parsing events...")
        context = etree.iterparse(self.event_src, events=('start', 'end',))
        root = True
        i = 0
        interval = max_events // 200
        for action, elem in context:
            if action == 'end' and (detag(elem) == "InitEvent" or detag(elem) == "RecvEvent" or detag(elem) == "SendEvent"):
                evt = defaultdict(lambda:None)
                evt["id"] = elem.get('eventId')
                evt["time"] = float( elem.get('time'))
                evt["elapsed"] = float( elem.get('elapsed'))
                evt["dev"]= elem.get('dev')
                evt["rts"] = int( elem.get('rts'),0)
                evt["seq"] = int( elem.get('seq'))
                evt["type"] = detag(elem).lower()[:4]

                if evt["type"] == "init":
                    evt["port"] = None
                    evt["send_id"] = None
                    evt["cancel"] = None
                    evt["fanout"] = None
                else:
                    evt["port"] = elem.get("port")

                    if evt["type"] == "send":
                        evt["cancel"] = bool(elem.get("cancel"))
                        evt["fanout"] = int(elem.get("fanout"))
                        evt["send_id"] = None

                    if evt["type"] == "recv":
                        evt["send_id"] = elem.get("sendEventId")
                        evt["cancel"] = None
                        evt["fanout"] = None

                for child in elem:
                    evt[detag(child).lower()] = json.loads("{" + child.text + "}")
                    
                self.ranges = self.compare_ranges(evt)
                values.append(self.build_event_values(evt))


                i += 1
                if i % batch == 0:
                    print("  Loading event " + str(i) + "...")
                    self.insert_rows("events", fields, values)
                    del values
                    values = []

                elem.clear()
            
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

                if i >= max_events:
                    break

        del context

        self.insert_rows("events", fields, values)

        print("  Finished parsing events.")
        print("  Creating indexes...")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_events_id ON events (id)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_events_dev ON events (dev)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_events_time ON events (time)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_events_type ON events (type)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_events_send_id ON events (send_id)")


    def device_states(self, graph_type):
        fields = []
        fields.append(Field("id", "string", set(["unique", "key", "not null"])))
        fields.append(Field("epoch", "integer", set(["unique", "key", "not null"])))
        fields.append(Field("init", "integer", set(["not null", "key"])))

        cols, fields = self.device_states_fields(graph_type)
        self.create_table("device_states", fields)
        print("  Parsing snapshots...")
        log = {}
        context = etree.iterparse(self.snap_src, events=('start', 'end',))

        orchTime = None
        seqNum = None
        graphTypeId = None
        graphInstId = None
        parent = None
        devRts = None
        devState = None
        devId = None

        for action, elem in context:
            name = elem.tag.split("}")[-1]
            if action == 'start':
                if name == "GraphSnapshot":
                    orchTime = elem.get('orchestratorTime')
                    seqNum = elem.get('sequenceNumber')
                    graphTypeId = elem.get('graphTypeId')
                    graphInstId = elem.get('graphInstId')
                    print("  Loading snapshots at epoch " + orchTime + "...")
                   
                    log = {"device_states": {}}

                elif name == "DevS":
                    parent = "DevS"
                    devState = None
                    devId = elem.get("id")
                    rts = elem.get("rts")
                    if rts:
                        devRts = int(rts)
                    else:
                        devRts = 0
                elif name == "S":
                    pass

            if action == 'end':
                if name == "S":
                    if parent == "DevS":
                        devState = parse_json(elem.text)
                elif name == "DevS":
                    log["device_states"][devId] = (devState, devRts)
                    devType=None
                    devId=None
                    parent = None
                    devRts = None

                elif name == "GraphSnapshot":
                    snapshot_values = []

                    if orchTime == "0" and seqNum == "0":
                        orchTime = "init"

                    for id, dev in log["device_states"].iteritems():
                        snapshot_values.append(self.build_snapshot_values(orchTime, id, dev, cols))

                    self.insert_rows("device_states", fields, snapshot_values)
                    self.snapshots.add(orchTime)
                    del snapshot_values
                
                elem.clear()

                while elem.getprevious() is not None:
                    del elem.getparent()[0]
        del context

        print("  Creating indexes...")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_id ON device_states (id)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_init ON device_states (init)")
        self.db.execute("CREATE INDEX IF NOT EXISTS index_device_states_epoch ON device_states (epoch)")

    def load_ranges(self):
        
        self.ranges["messages_sent"] = [0, float("-inf")]
        self.ranges["messages_received"] = [0, float("-inf")]

        for sent in self.message_counts["send"].values():
            self.ranges["messages_sent"][1] = max(sent, self.ranges["messages_sent"][1])

        for sent in self.message_counts["recv"].values():
            self.ranges["messages_received"][1] = max(sent, self.ranges["messages_received"][1])

        range_values = [(k, v[0], v[1]) for k, v in self.ranges.iteritems()]

        self.create_table("state_ranges", self.range_fields())


        self.insert_rows("state_ranges", self.range_fields(), range_values)


    def ranges_init(self, graph_type):
        self.ranges = {}
        for s in self.device_states_fields(graph_type)[1]:
            if s.name != "epoch" and s.name != "init" and (s.type == "INTEGER" or s.type == "REAL"):
                self.ranges[s.name] = [float("inf"), float("-inf")]

    def aggregate_states_fields(self, fields):
        fields.append(Field("parent", "int", set(["key"])))
        fields[0] = Field("partition_id", "int")
        
        return fields

    def compare_ranges(self, evt):
        values = defaultdict(lambda:None, evt["s"])
        for k, v in values.iteritems():
            if k in self.ranges and (isinstance(v, int) or isinstance(v, float) or isdigit(v)):
                if isinstance(v, str):
                    val = float(v)
                else:
                    val = v
                self.ranges[k][0] = min(self.ranges[k][0], val)
                self.ranges[k][1] = max(self.ranges[k][1], val)

        return self.ranges

    def build_snapshot_values(self, epoch, id, dev, col = None):
        value = defaultdict(lambda:None, dev[0])
        if epoch == "init":
            value["init"] = 1
            value["epoch"] = 0
        else:
            value["init"] = 0
            value["epoch"] = epoch

        value["id"] = id
        value["rts"] = dev[1]

        for k, v in value.iteritems():
            if isinstance(v, list):
                value[k] = str(v)

        if col:
            for i in col:
                if i not in value:
                    value[i] = None

        return value


    def build_event_values(self, evt):
        if evt["type"] != "recv":
            evt["m"] = json.dumps(evt["m"])

        if evt["type"] == "recv":
            self.message_counts["recv"][evt["dev"]] += 1

        if evt["type"] == "send":
            self.message_counts["send"][evt["dev"]] += 1

        evt["s"] = json.dumps(evt["s"])
        self.max_time = min(evt["time"], self.max_time)
        return evt


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
        print("  Inserting {} records to {}...".format(len(values), table_name))
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



