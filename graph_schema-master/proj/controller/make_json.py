import json
import uuid
import cloudstorage as gcs
from google.appengine.api import app_identity
from google.appengine.ext import blobstore

from controller.graph.core import *
from controller.graph.events import *
from controller.graph.load_xml import *

def merge_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z

class JSONStreamBuilder():
	def __init__(self, graph_src, event_src):
		self.graph = load_graph(graph_src, graph_src)
		event_writer = LogWriter()
		parseEvents(event_src, event_writer)
		self.events = event_writer.log

	def format_properties(self, props):
		if props is None:
			return

		res = {}

		for p, val in props.elements_by_name.items():
			if isinstance(val, ArrayTypedDataSpec):
				arr = []
				for v in val.create_default():
					arr.append(v)
				res[p] = arr
			else:
				res[p] = val.default
		return res

	def graph_instance_json(self):
		id = self.graph.id
		graph_type = self.graph.graph_type.id
		properties = self.graph.properties
		metadata = self.graph.metadata

		content = {"kind": "bigquery#tableDataInsertAllRequest",
					"rows": [{"json": {"id": id, 
								"type": graph_type,
								"properties": properties,
								"metadata": metadata}}]}

		return content


	def dev_instance_json(self):
		body = {"kind": "bigquery#tableDataInsertAllRequest",
				"rows": []}

		for id, d in self.graph.device_instances.items():
			body["rows"].append({"json": {"id": d.id, 
										"parent_id": d.parent.id,
										"type": d.device_type.id,
										"properties": json.dumps(d.properties),
										"metadata": d.metadata}})
		
		return body


	def dev_json(self):
		inserted_dev_type = set()
		body = {"kind": "bigquery#tableDataInsertAllRequest",
				"rows": []}
		port_body = {"kind": "bigquery#tableDataInsertAllRequest",
				"rows": []}

		for id, d in self.graph.device_instances.items():
			dev = d.device_type
			if dev.id not in inserted_dev_type:
				body["rows"].append({"json": {"id": dev.id,
											"parent_id": dev.parent.id,
											"state":  json.dumps(self.format_properties(dev.state)),
											"properties": json.dumps(self.format_properties(dev.properties)),
											"metadata": dev.metadata}})

				port_body["rows"].extend(self.port_json(dev.ports))
				inserted_dev_type.add(dev.id)

		return {"type": body, "port": port_body}

	def port_json(self, ports):
		body = {"kind": "bigquery#tableDataInsertAllRequest",
				"rows": []}

		for id, p in ports.items():
			row = {}
			base = {"dev_type_id": p.parent.id,
							"name": p.name}
			
			if isinstance(p, InputPort):
				child = {"type": "input",
						"message_type_id": p.message_type.id,
						"properties": json.dumps(self.format_properties(p.properties)),
						"state":  json.dumps(self.format_properties(p.state)),
						"metadata": p.metadata}
			elif isinstance(p, OutputPort):
				child = {"type": "output",
						"message_type_id": p.message_type.id,
						"properties": None,
						"state": None,
						"metadata": p.metadata}
			else:
				child = {"type": None,
						"message_type_id": p.message_type.id,
						"properties": None,
						"state": None,
						"metadata": p.metadata}

			row["json"] = merge_dicts(base, child)

			body["rows"].append(row)

		return body


	def edge_instance_json(self):
		body = {"kind": "bigquery#tableDataInsertAllRequest",
				"rows": []}

		for id, e in self.graph.edge_instances.items():
			body["rows"].append({"json": {"parent": e.parent.id,
									"source": e.src_device.id,
									"target": e.dst_device.id,
									"source_port": e.src_port.name,
									"target_port": e.dst_port.name,
									"message_type": e.message_type.id,
									"properties": json.dumps(e.properties),
									"metadata": e.metadata}})

		return body

	def event_json(self):
		body = {"kind": "bigquery#tableDataInsertAllRequest",
				"rows": []}

		for id, e in self.events.items():
			row = {}
			base = {"event_id": e.eventId,
					"time": e.time,
					"elapsed": e.elapsed,
					"dev": e.dev,
					"rts": e.rts,
					"seq": e.seq,
					"L": e.L,
					"S": json.dumps(e.S)}

			if isinstance(e, InitEvent):
				child = {"M": None,
						"port": None,
						"cancel": None,
						"fanout": None,
						"send_event_id": None,
						"type": "init"}

			if isinstance(e, SendEvent):
				child = {"M": json.dumps(e.M),
						"port": e.port,
						"cancel":  e.cancel,
						"fanout": e.fanout,
						"send_event_id": None,
						"type": "send"}

			if isinstance(e, RecvEvent):
				child = {"M": None,
						"port": None,
						"cancel": None,
						"fanout": None,
						"send_event_id": e.sendEventId,
						"type": "recv"}

			row["json"] = merge_dicts(base, child)
			body["rows"].append(row)

		return body




class BigQueryStreamBuilder():
	def make_local_database(graph_src, event_src):
		graph = load_graph(graph_src, graph_src)

		graph_instance_json = make_graph_instance_json(graph)
		device_instance_json = make_dev_instance_json(graph.device_instances)
		device_types_json = make_dev_type_json(graph.device_instances)
		edge_instance_json = make_edge_instance_json(graph.edge_instances)

		events = LogWriter()
		parseEvents(event_src, events)
		events_json = make_event_json(events.log)

		graph_table.write(graph_instance_json)
		device_instance_table.write(device_instance_json)
		device_type_table.write(device_types_json[0])
		device_port_table.write(device_types_json[1])
		edge_instance_table.write(edge_instance_json)
		event_table.write(events_json)


class CloudStorageBuilder():
	def __init__(self, page_handler): 
		self.bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())
		self.page_handler = page_handler
	
	def make_bigquery_database(self, graph_src, event_src):
		graph = load_graph(graph_src, graph_src)
		graph_instance_csv = make_graph_instance_json(graph)
		device_instance_csv = make_dev_instance_json(graph.device_instances)
		device_types_csv = make_dev_type_json(graph.device_instances)
		edge_instance_csv = make_edge_instance_json(graph.edge_instances)
		events = LogWriter()
		parseEvents(event_src, events)
		events_csv = make_event_json(events.log)

		self.stream_json('graph_instances', graph_instance_json)
		self.stream_json('device_instances', device_instance_json)
		self.stream_json('device_types', device_types_json[0])
		self.stream_json('device_ports', device_types_json[1])
		self.stream_json('edge_instances', edge_instance_json)
		self.stream_json('events', events_json)
