import json
import uuid
import cloudstorage as gcs
from google.appengine.api import app_identity
from google.appengine.ext import blobstore

from controller.graph.core import *
from controller.graph.events import *
from controller.graph.load_xml import *



def format_properties(props):
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

def make_graph_instance_row(graph):
	id = graph.id
	graph_type = graph.graph_type.id
	properties = graph.properties
	metadata = graph.metadata

	header = "id|type|properties|metadata\n"
	content = "{}|{}|{}|{}\n".format(id, graph_type, properties, metadata)

	return header + content


def make_dev_instance_row(devices):
	header = "id|parent_id|type|properties|metadata\n"
	content = ""

	for id, d in devices.items():
		content += "{}|{}|{}|{}|{}\n".format(d.id, d.parent.id, d.device_type.id, json.dumps(d.properties), d.metadata)
	
	return header + content

def make_dev_type_row(devices):
	inserted_dev_type = set()
	header = "id|parent_id|state|properties|metadata\n"
	content = ""
	port_header = "dev_type_id|name|type|message_type_id|properties|state|metadata\n"
	port_content = ""

	for id, d in devices.items():
		dev = d.device_type
		if dev.id not in inserted_dev_type:
			content +=  "{}|{}|{}|{}|{}\n".format(dev.id, dev.parent.id, json.dumps(format_properties(dev.state)),json.dumps(format_properties(dev.properties)), dev.metadata)
			port_content += make_port_row(dev.ports)
			inserted_dev_type.add(dev.id)

	return [header + content, port_header + port_content]

def make_port_row(ports):
	content = ""
	for id, p in ports.items():
		content += "{}|{}|".format(p.parent.id,p.name)
		if isinstance(p, InputPort):
			content += "input|{}|{}|{}|{}\n".format(p.message_type.id,json.dumps(format_properties(p.properties)),json.dumps(format_properties(p.state)),p.metadata)
		elif isinstance(p, OutputPort):
			content += "output|{}|||{}\n".format(p.message_type.id,p.metadata)
		else:
			content += "|{}|||{}\n".format(p.message_type.id,p.metadata)

	return content


def make_edge_instance_row(edges):
	"""
	    self.dst_device=dst_device
        self.src_device=src_device
        self.message_type=dst_port.message_type
        self.dst_port=dst_port
        self.src_port=src_port
        self.properties=properties
        self.metadata=metadata
    """
	header = "parent|source|target|source_port|target_port|message_type|properties|metadata\n"
	content = ""

	for id, e in edges.items():
		content += "{}|{}|{}|{}|{}|{}|{}|{}\n".format(e.parent.id, e.src_device.id, e.dst_device.id, e.src_port.name, e.dst_port.name, e.message_type.id, json.dumps(e.properties), e.metadata)

	return header + content


def make_event_row(events):
	header = "event_id|time|elapsed|dev|rts|seq|L|S|M|port|cancel|fanout|send_event_id|type\n"
	content = ""

	for id, e in events.items():
		content += "{}|{}|{}|{}|{}|{}|{}|{}|".format(e.eventId, e.time, e.elapsed, e.dev, e.rts, e.seq, e.L, json.dumps(e.S))

		if isinstance(e, InitEvent):
			content += "|||||init\n"

		if isinstance(e, SendEvent):
			content += "{}|{}|{}|{}||send\n".format(json.dumps(e.M), e.port, e.cancel, e.fanout)

		if isinstance(e, RecvEvent):
			content += "|{}|||{}|recv\n".format(e.port, e.sendEventId)

	return header + content


def make_local_database(graph_src, event_src):
	graph_table = open("data/graph_instances.csv", "w+")
	device_instance_table = open("data/device_instances.csv", "w+")
	device_type_table = open("data/device_types.csv", "w+")
	device_port_table = open("data/device_ports.csv", "w+")
	edge_instance_table = open("data/edge_instances.csv", "w+")
	event_table = open("data/events.csv", "w+")

	graph = load_graph(graph_src, graph_src)

	graph_instance_csv = make_graph_instance_row(graph)
	device_instance_csv = make_dev_instance_row(graph.device_instances)
	device_types_csv = make_dev_type_row(graph.device_instances)
	edge_instance_csv = make_edge_instance_row(graph.edge_instances)

	events = LogWriter()
	parseEvents(event_src, events)
	events_csv = make_event_row(events.log)

	graph_table.write(graph_instance_csv)
	device_instance_table.write(device_instance_csv)
	device_type_table.write(device_types_csv[0])
	device_port_table.write(device_types_csv[1])
	edge_instance_table.write(edge_instance_csv)
	event_table.write(events_csv)


class CloudStorageBuilder():
	def __init__(self, page_handler): 
		self.bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())
		self.page_handler = page_handler
	
	def make_cloud_database(self, graph_src, event_src):
		graph = load_graph(graph_src, graph_src)
		graph_instance_csv = make_graph_instance_row(graph)
		device_instance_csv = make_dev_instance_row(graph.device_instances)
		device_types_csv = make_dev_type_row(graph.device_instances)
		edge_instance_csv = make_edge_instance_row(graph.edge_instances)
		events = LogWriter()
		parseEvents(event_src, events)
		events_csv = make_event_row(events.log)
		self.write_csv_to_cloud('graph_instances.csv', graph_instance_csv)
		self.write_csv_to_cloud('device_instances.csv', device_instance_csv)
		self.write_csv_to_cloud('device_types.csv', device_types_csv[0])
		self.write_csv_to_cloud('device_ports.csv', device_types_csv[1])
		self.write_csv_to_cloud('edge_instances.csv', edge_instance_csv)
		self.write_csv_to_cloud('events.csv', events_csv)

	def write_csv_to_blob(self, filename, content):
		upload_url = blobstore.create_upload_url()

	def write_csv_to_cloud(self, filename, content):
		filename = '/' + self.bucket_name + '/' + filename
		write_retry_params = gcs.RetryParams(backoff_factor=1.1)
		gcs_file = gcs.open(filename,
                      'w',
                      content_type='text/csv',
                      retry_params=write_retry_params)
		gcs_file.write(content)
		gcs_file.close()
		self.page_handler.tmp_filenames_to_clean_up.append(filename)
