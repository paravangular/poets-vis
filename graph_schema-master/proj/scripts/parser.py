from collections import defaultdict
import json

class Parser():
    def __init__(self):
        pass

    def detag(self, elem):
        return elem.tag.split("}")[-1]

    def load_properties(self, prop):
        s = self.detag(prop)
        name = prop.get("name")
        prop_type = prop.get("type")

        if s == "Array":
            prop_type = "[" + prop_type + ", " + prop.get("length") + "]"

        return (name, prop_type)

    def parse_graph_type(self, elem):
        print("Parsing graph type...")
        graph = {"device_types": {}}
        graph["id"] = elem.get("id")
        
        for child in elem:
            child_name = self.detag(child)
        
            if child_name == "Properties":
                graph["properties"] = set()
                
                for prop in child:
                    graph["properties"].add(self.load_properties(prop))
            
            if child_name == "Metadata":
                graph["metadata"] = json.loads("{"+ child.text+"}")
            
            if child_name == "MessageTypes":
                graph["message_types"] = {}
                
                for msg_type in child:
                    if self.detag(msg_type) == "MessageType":
                        graph["message_types"][msg_type.get("id")] = set()
                        
                        for msg in msg_type:
                            for prop in msg:
                                graph["message_types"][msg_type.get("id")].add(self.load_properties(prop))
            
            if child_name == "DeviceTypes":
                for dev in child:
                    dev_id = dev.get("id")
            
                    if self.detag(dev) == "DeviceType":
                        graph["device_types"][dev_id] = {"properties": set(), "state": set(), "ports": {"input": {}, "output": {}}}
                    
                        for s in dev:
                            s_name = self.detag(s)
                        
                            if s_name == "Properties" or s_name == "State":
                                for prop in s:
                                    graph["device_types"][dev_id][s_name.lower()].add(self.load_properties(prop))
                            elif s_name == "InputPort":
                                port_name = s.get("name")
                                graph["device_types"][dev_id]["ports"]["input"][port_name] = {"name": port_name, "message_type": s.get("messageTypeId"), "properties": set(), "state": set()}
            
                                for props in s:
                                    props_type = self.detag(props)
                                
                                    if props_type == "State" or props_type == "Properties":
                                        
                                        for prop in props:
                                            graph["device_types"][dev_id]["ports"]["input"][port_name][props_type.lower()].add(self.load_properties(prop))
                            
                            elif s_name == "OutputPort":
                                port_name = s.get("name")
                                graph["device_types"][dev_id]["ports"]["output"][port_name] = {"name": port_name, "message_type": s.get("messageTypeId")}
        
        return graph

    def parse_events(self, elem):
        if self.detag(elem) == "InitEvent" or self.detag(elem) == "RecvEvent" or self.detag(elem) == "SendEvent":
            evt = defaultdict(lambda:None)
            evt["id"] = elem.get('eventId')
            evt["time"] = float( elem.get('time'))


            evt["elapsed"] = float( elem.get('elapsed'))
            evt["dev"]= elem.get('dev')
            evt["rts"] = int( elem.get('rts'),0)
            evt["seq"] = int( elem.get('seq'))
            evt["type"] = self.detag(elem).lower()[:4]

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
                evt[self.detag(child).lower()] = json.loads("{" + child.text + "}")

            return evt

        return None
