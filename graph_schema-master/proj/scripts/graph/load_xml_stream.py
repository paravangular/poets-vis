
import xml.etree.ElementTree as ET
from lxml import etree
from collections import defaultdict

import os
import sys
import json







def load_graph_type_and_instances(src, db, parser):
	context = etree.iterparse(src, events=('start', 'end',))

	curr_graph = {"device_instances": {}, "edge_instances": []}
	tags = set(["GraphType", "DevI", "DeviceInstances", "EdgeI", "EdgeInstances"])
	props = None


	for action, elem in context:
		name = parser.detag(elem)
		if action == 'end' and name in tags:
			if name == "GraphType":
				graph_type = parser.parse_graph_type(elem)

			if name == "DevI":
				# TODO: assert parent:
				curr_graph["device_instances"][elem.get("id")] = {"id": elem.get("id"), "type": elem.get("type")}
				
				for child in elem:
					if parser.detag(child) == "P":
						curr_graph["device_instances"][elem.get("id")]["properties"] = json.loads("{" + child.text + "}")

			if name == "DeviceInstances":
				pass

			if name == "EdgeI":
				edge = elem.get("path").split("-")
				source, source_port = edge[1].split(":")
				dest, dest_port = edge[0].split(":")

				curr_graph["edge_instances"].append({"source": source, "target": dest, "source_port": source_port, "target_port": dest_port})

			if name == "EdgeInstances":
				pass

			if name == "GraphInstance":
				for child in elem:
					print(child)
					if parser.detag(child) == "Properties":
						props = json.loads("{" + child.text + "}")
				

			elem.clear()
			while elem.getprevious() is not None:
				del elem.getparent()[0]

			
	del context

	return graph_type, curr_graph, props


