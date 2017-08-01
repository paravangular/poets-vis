from graph.core import *

from graph.load_xml import load_graph_types_and_instances
from graph.save_xml import save_graph
import sys
import os
import math


import os
appBase=os.path.dirname(os.path.realpath(__file__))

src=appBase+"/token_ring.xml"
(graphTypes,graphInstances)=load_graph_types_and_instances(src,src)

n = 2    

graphType=graphTypes["token_ring"]
devType=graphType.device_types["device"]

instName="token_ring_{}_{}".format(n,n)
properties={}
res=GraphInstance(instName, graphType, properties)
nodes={}

for i in range(0,n):
    sys.stderr.write(" Device {}\n".format(i + 1))
    
    if initToken:
        devProps={"hasInitToken": 1}
    else:
        devProps={"hasInitToken": 0}
    
    di=DeviceInstance(res,"n_{}".format(i + 1), devType, devProps)
    nodes[i]=di
    res.add_device_instance(di)
        
def add_channel(s, d):
    dst=nodes[s]
    src=nodes[d]
    ei=EdgeInstance(res, d,"in", s,"out")
    res.add_edge_instance(ei)


for i in range(0,n):
    add_channel(i, (i + 1) % n)

save_graph(res,sys.stdout)        
