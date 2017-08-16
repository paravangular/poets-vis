
import xml.etree.ElementTree as ET
from lxml import etree
from collections import defaultdict

import os
import sys
import json

def detag(elem):
	return elem.tag.split("}")[-1]

def load_properties(prop):
	s = detag(prop)
	name = prop.get("name")
	prop_type = prop.get("type")

	if s == "Array":
		prop_type = "[" + prop_type + ", " + prop.get("length") + "]"

	return (name, prop_type)

def load_graph_type(elem):
	print("Parsing graph type...")
	graph = {"device_types": {}}
	graph["id"] = elem.get("id")
	
	for child in elem:
		child_name = detag(child)
	
		if child_name == "Properties":
			graph["properties"] = set()
			
			for prop in child:
				graph["properties"].add(load_properties(prop))
		
		if child_name == "Metadata":
			graph["metadata"] = json.loads("{"+ child.text+"}")
		
		if child_name == "MessageTypes":
			graph["message_types"] = {}
			
			for msg_type in child:
				if detag(msg_type) == "MessageType":
					graph["message_types"][msg_type.get("id")] = set()
					
					for msg in msg_type:
						for prop in msg:
							graph["message_types"][msg_type.get("id")].add(load_properties(prop))
		
		if child_name == "DeviceTypes":
			for dev in child:
				dev_id = dev.get("id")
		
				if detag(dev) == "DeviceType":
					graph["device_types"][dev_id] = {"properties": set(), "state": set(), "ports": {"input": {}, "output": {}}}
				
					for s in dev:
						s_name = detag(s)
					
						if s_name == "Properties" or s_name == "State":
							for prop in s:
								graph["device_types"][dev_id][s_name.lower()].add(load_properties(prop))
						elif s_name == "InputPort":
							port_name = s.get("name")
							graph["device_types"][dev_id]["ports"]["input"][port_name] = {"name": port_name, "message_type": s.get("messageTypeId"), "properties": set(), "state": set()}
		
							for props in s:
								props_type = detag(props)
							
								if props_type == "State" or props_type == "Properties":
									
									for prop in props:
										graph["device_types"][dev_id]["ports"]["input"][port_name][props_type.lower()].add(load_properties(prop))
						
						elif s_name == "OutputPort":
							port_name = s.get("name")
							graph["device_types"][dev_id]["ports"]["output"][port_name] = {"name": port_name, "message_type": s.get("messageTypeId")}
	
	return graph


def load_graph_type_and_instances(src, db):
	context = etree.iterparse(src, events=('start', 'end',))

	curr_graph = {"device_instances": {}, "edge_instances": []}
	tags = set(["GraphType", "DevI", "DeviceInstances", "EdgeI", "EdgeInstances"])
	props = None


	for action, elem in context:
		name = detag(elem)
		if action == 'end' and name in tags:
			if name == "GraphType":
				graph_type = load_graph_type(elem)

			if name == "DevI":
				# TODO: assert parent:
				curr_graph["device_instances"][elem.get("id")] = {"id": elem.get("id"), "type": elem.get("type")}
				
				for child in elem:
					if detag(child) == "P":
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
					if detag(child) == "Properties":
						props = json.loads("{" + child.text + "}")
				

			elem.clear()
			while elem.getprevious() is not None:
				del elem.getparent()[0]

			
	del context

	return graph_type, curr_graph, props


