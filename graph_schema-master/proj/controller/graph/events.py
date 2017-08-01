import xml.sax
import json
import sys

import xml.etree.ElementTree as ET
from lxml import etree

# from controller.graph.core import expand_typed_data
# from controller.graph.load_xml import *

from graph.core import expand_typed_data
from graph.load_xml import *

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
        self.log = {};
        self.event_pairs = []

    def onInitEvent(self,initEvent):
        if initEvent.eventId not in self.log:
            self.log[initEvent.eventId] = initEvent
    
    def onSendEvent(self,sendEvent):
        if sendEvent.eventId not in self.log:
            self.log[sendEvent.eventId] = sendEvent
    
    def onRecvEvent(self,recvEvent):
        if recvEvent.eventId not in self.log:
            self.log[recvEvent.eventId] = recvEvent
            self.event_pairs.append(recvEvent.sendEventId + ":" + recvEvent.eventId)

def extractInitEvent(n,writer):
    eventId=get_attrib(n,"eventId")
    time=float(get_attrib(n,"time"))
    elapsed=float(get_attrib(n,"elapsed"))
    dev=get_attrib(n,"dev")
    rts=int(get_attrib(n,"rts"),0)
    seq=int(get_attrib(n,"seq"))
    
    L=[]
    for l in n.findall("p:L",ns):
        L.append(l.text)
    
    S=n.find("p:S",ns)
    if S is not None:
        #print(S.text)
        S=json.loads("{"+S.text+"}")
    
    e=InitEvent(
        eventId, time, elapsed,
        dev, rts, seq, L, S
    )
    writer.onInitEvent(e)
    
def extractSendEvent(n,writer):
    eventId=get_attrib(n,"eventId")
    time=float(get_attrib(n,"time"))
    elapsed=float(get_attrib(n,"elapsed"))
    dev=get_attrib(n,"dev")
    rts=int(get_attrib(n,"rts"),0)
    seq=int(get_attrib(n,"seq"))
    
    L=[]
    for l in n.findall("p:L",ns):
        L.append(l.text)
    
    S=n.find("p:S",ns)
    if S is not None:
        S=json.loads("{"+S.text+"}")
        
    port=get_attrib(n,"port")
    cancel=bool(get_attrib(n,"cancel"))
    fanout=int(get_attrib(n,"fanout"))
    
    M=n.find("p:M",ns)
    if M is not None:
        M=json.loads("{"+M.text+"}")
    
    writer.onSendEvent( SendEvent(
        eventId, time, elapsed,
        dev, rts, seq, L, S,
        port,
        cancel, fanout, M
    ) )

def extractRecvEvent(n,writer):
    eventId=get_attrib(n,"eventId")
    time=float(get_attrib(n,"time"))
    elapsed=float(get_attrib(n,"elapsed"))
    dev=get_attrib(n,"dev")
    rts=int(get_attrib(n,"rts"),0)
    seq=int(get_attrib(n,"seq"))
    
    L=[]
    for l in n.findall("p:L",ns):
        L.append(l.text)
    
    S=n.find("p:S",ns)
    if S is not None:
        S=json.loads("{"+S.text+"}")
        
    port=get_attrib(n,"port")
    sendEventId=get_attrib(n,"sendEventId")
    
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

def parseEvents(src,writer):
    tree = etree.parse(src)
    doc = tree.getroot()
    eventsNode = doc;

    if deNS(eventsNode.tag)!="p:GraphLog":
        raise XMLSyntaxError("Expected GraphLog tag.", eventsNode)

    for e in eventsNode.findall("p:*",ns):
        extractEvent(e,writer)

        
