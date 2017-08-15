import xml.sax
import json
import sys

import xml.etree.cElementTree as ET
from lxml import etree


from scripts.graph.core import expand_typed_data
from scripts.graph.load_xml import *
def parse_json(text):
    if text is None or text=="":
        return None

    j = json.loads("{"+text+"}")
    return j

def parseSnapshot(src):
    print("Parsing snapshots...")
    log = {}
    context = etree.iterparse(src, events=('start', 'end',))

    orchTime = None
    seqNum = None
    graphTypeId = None
    graphInstId = None
    parent = None
    devRts = None
    devState = None
    devId = None

    for action, elem in context:
        name = deNS(elem.tag).split("}")[-1]
        if action == 'start':
            if name == "GraphSnapshot":
                orchTime = elem.get('orchestratorTime')
                seqNum = elem.get('sequenceNumber')
                graphTypeId = elem.get('graphTypeId')
                graphInstId = elem.get('graphInstId')

                print("  loading snapshots at epoch " + orchTime)
                if orchTime == "0" and seqNum == "0":
                    log["init"] = {"device_states": {}}
                else:
                    log[orchTime] = {"device_states": {}}

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
                if orchTime == "0" and seqNum == "0":
                    log["init"]["device_states"][devId] = (devState, devRts)
                else:
                    log[orchTime]["device_states"][devId] = (devState, devRts)
                devType=None
                devId=None
                parent = None
                devRts = None

            elif name == "GraphSnapshot":
               pass

        
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    return log



def extractSnapshotInstances(graphInstances,src):
    class SnapshotReaderEventsUpdate(SnapshotReaderEvents):
        def __init__(self,graphInstances):
            SnapshotReaderEvents.__init__(self)
            self.graphInstances=graphInstances
            self.selGraphInstance=None
            self.sink={}

        def onStartSnapshot(self,graphType,graphInstanceId,orchTime,seqNum):
            
            self.selGraphInstance=self.graphInstances
            self.selGraphType=self.selGraphInstance.graph_type

            gi=self.selGraphInstance
            self.orchTime=orchTime
            self.seqNum=seqNum
            self.deviceStates={ id : (None,0) for id in gi.device_instances.keys() } # Tuples of (state,rts)
            # self.edgeStates={ id : (None,0,[]) for id in gi.edge_instances.keys() } # tuples of (state,firings,messages)
            print("  loading snapshot at time " + str(self.orchTime))

        def onEndSnapshot(self):
            gi=self.selGraphInstance
            for di in gi.device_instances.values():
                dt=gi.device_instances[di.id].device_type
                val=self.deviceStates[di.id]
                if dt.state and None==val[0]:
                    val=(dt.state.create_default(),val[1])
                    self.deviceStates[di.id]=val

            # for ei in gi.edge_instances.values():
            #     et=gi.edge_instances[ei.id].message_type
            #     dt=gi.edge_instances[ei.id].dst_port
            #     val=self.edgeStates[ei.id]
            #     if dt.state and not val[0]:
            #         assert(val[1]==0 and val[2]==[]) # Must not have seen firings or messages if we didn't get state
            #         val=(et.state.create_default(),val[1],val[2])
            #         self.edgeStates[ei.id]=val

            if self.orchTime == '0' and self.seqNum == '0':
                self.sink["init"] = {"device_states": self.deviceStates} #, "edge_states": self.edgeStates}
            elif self.orchTime not in self.sink:
                self.sink[self.orchTime] = {"device_states": self.deviceStates} #, "edge_states": self.edgeStates}

            self.selGraphType=None
            self.selGraphInstance=None
            self.deviceStates=None
            # self.edgeStates=None
        

        def onDeviceInstance(self,id,state,rts):
            devType=self.selGraphInstance.device_instances[id].device_type
            expanded=expand_typed_data(devType.state,state)
            self.deviceStates[id]=(expanded,rts)

        # def onEdgeInstance(self,id,state,firings,messages):
        #     edgeType=self.selGraphInstance.edge_instances[id].message_type
        #     dstPort=self.selGraphInstance.edge_instances[id].dst_port
        #     messages=[expand_typed_data(edgeType.message_type, msg) for msg in messages]
        #     self.edgeStates[id]=(expand_typed_data(dstPort.state,state),firings,messages)

    print("Parsing snapshots...")
    events=SnapshotReaderEventsUpdate(graphInstances)
    parseSnapshot(src,events)

    print("Finished loading snapshots.")
    return events.sink
