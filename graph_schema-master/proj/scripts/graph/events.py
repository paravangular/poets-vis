import xml.sax
import json
import sys

import xml.etree.cElementTree as ET
from lxml import etree

# from controller.graph.core import expand_typed_data
# from controller.graph.load_xml import *

from scripts.graph.core import expand_typed_data
from scripts.graph.load_xml import *

class Event(object):
    def __init__(self, eventId, time, elapsed):
        self.eventId=eventId
        self.time=time
        self.elapsed=elapsed
        
class DeviceEvent(Event):
    def __init__(self,
        eventId, time, elapsed,
        dev, rts, seq, L, S
    ):
        Event.__init__(self, eventId, time, elapsed)
        self.dev=dev
        self.rts=rts
        self.seq=seq
        self.L=L
        self.S=S

class InitEvent(DeviceEvent):
    def __init__(self,
        eventId, time, elapsed,
        dev, rts, seq, L, S
    ):
        DeviceEvent.__init__(self,
            eventId,time,elapsed,
            dev, rts, seq, L, S
        )
        self.type="init"


class MessageEvent(DeviceEvent):
    def __init__(self,
        eventId, time, elapsed,
        dev, rts, seq, L, S,
        port
    ):
        DeviceEvent.__init__(self,
            eventId,time,elapsed,
            dev, rts, seq, L, S
        )
        self.port=port
        
class SendEvent(MessageEvent):
    def __init__(self,
        eventId, time, elapsed,
        dev, rts, seq, L, S,
        port,
        cancel, fanout, M
    ):
        MessageEvent.__init__(self,
            eventId,time,elapsed,
            dev, rts, seq, L, S,
            port
        )
        self.cancel=cancel
        self.fanout=fanout
        self.M=M
        self.type="send"

class RecvEvent(MessageEvent):
    def __init__(self,
        eventId, time, elapsed,
        dev, rts, seq, L, S,
        port,
        sendEventId
    ):
        MessageEvent.__init__(self,
            eventId,time,elapsed,
            dev, rts, seq, L, S,
            port
        )
        self.sendEventId=sendEventId
        self.type="recv"

class LogWriter(object):
    def __init__(self):
        self.log = {"init": {}, "msg": {}};
        self.event_pairs = []
        self.max_time = 0

    def onInitEvent(self,initEvent):
        if initEvent.eventId not in self.log["init"]:
            self.log["init"][initEvent.eventId] = initEvent

    
    def onSendEvent(self,sendEvent):
        if sendEvent.eventId not in self.log["msg"]:
            self.log["msg"][sendEvent.eventId] = sendEvent
            self.max_time = max(sendEvent.time, self.max_time)
    
    def onRecvEvent(self,recvEvent):
        if recvEvent.eventId not in self.log["msg"]:
            self.log["msg"][recvEvent.eventId] = recvEvent
            self.event_pairs.append(recvEvent.sendEventId + ":" + recvEvent.eventId)
            self.max_time = max(recvEvent.time, self.max_time)

def extractInitEvent(n,writer):
    eventId = n.get('eventId')
    time=float( n.get('time'))
    elapsed=float( n.get('elapsed'))
    dev= n.get('dev')
    rts=int( n.get('rts'),0)
    seq=int( n.get('seq'))
    
    L=[]
    S = None
    for child in n:
        if deNS(child.tag) == "p:L":
            L.append(child.text)

        if deNS(child.tag) == "p:S":
            S = json.loads("{" + child.text + "}")
    
    e=InitEvent(
        eventId, time, elapsed,
        dev, rts, seq, L, S
    )
    writer.onInitEvent(e)
    
def extractSendEvent(n,writer):
    eventId = n.get('eventId')
    time=float( n.get('time'))
    elapsed=float( n.get('elapsed'))
    dev= n.get('dev')
    rts=int( n.get('rts'),0)
    seq=int( n.get('seq'))
    
    L=[]
    S = None
    M = None
    for child in n:
        if deNS(child.tag) == "p:L":
            L.append(child.text)

        if deNS(child.tag) == "p:S":
            S = json.loads("{" + child.text + "}")

        if deNS(child.tag) == "p:M":
            M = json.loads("{"+ child.text+"}")

        
    port=n.get("port")
    cancel=bool(n.get("cancel"))
    fanout=int(n.get("fanout"))
    
    writer.onSendEvent( SendEvent(
        eventId, time, elapsed,
        dev, rts, seq, L, S,
        port,
        cancel, fanout, M
    ) )

def extractRecvEvent(n,writer):
    eventId = n.get('eventId')
    time=float( n.get('time'))
    elapsed=float( n.get('elapsed'))
    dev= n.get('dev')
    rts=int( n.get('rts'),0)
    seq=int( n.get('seq'))
    
    L=[]
    S = None
    for child in n:
        if deNS(child.tag) == "p:L":
            L.append(child.text)

        if deNS(child.tag) == "p:S":
            S = json.loads("{" + child.text + "}")
        
    port=n.get("port")
    sendEventId=n.get("sendEventId")
    
    writer.onRecvEvent( RecvEvent(
        eventId, time, elapsed,
        dev, rts, seq, L, S,
        port,
        sendEventId
    ) )


def extractEvent(n,writer):
    if deNS(n.tag)=="p:InitEvent":
        extractInitEvent(n,writer)
    elif deNS(n.tag)=="p:SendEvent":
        extractSendEvent(n,writer)
    elif deNS(n.tag)=="p:RecvEvent":
        extractRecvEvent(n,writer)
    else:
        raise XMLSyntaxError("DIdn't understand node type.", n)

# def parseEvents(src,writer):
#     tree = etree.parse(src)
#     doc = tree.getroot()
#     eventsNode = doc;

#     if deNS(eventsNode.tag)!="p:GraphLog":
#         raise XMLSyntaxError("Expected GraphLog tag.", eventsNode)

#     for e in eventsNode.findall("p:*",ns):
#         extractEvent(e,writer)


def detag(elem):
    return elem.tag.split("}")[-1]

def parse_events(src, max_events = 10000000, batch = 100000):
    print("Parsing events...")
    context = etree.iterparse(src, events=('start', 'end',))
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

            if evt["type"] != "init":
                evt["port"] = elem.get("port")

            if evt["type"] == "send":
                evt["cancel"] = bool(elem.get("cancel"))
                evt["fanout"] = int(elem.get("fanout"))

            for child in elem:
                evt[detag(child).lower()] = json.loads("{" + child.text + "}")
                
            values.append(evt)

            i += 1
            if batch % i == 0:
                self.insert_rows("events", fields, values)
                del values
                values = []

            elem.clear()
        
            while elem.getprevious() is not None:
                del elem.getparent()[0]

            if i >= max_events:
                break

    del context
    print("Finished parsing events.")