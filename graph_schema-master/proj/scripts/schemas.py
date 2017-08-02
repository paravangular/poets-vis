from google.cloud.bigquery import SchemaField

GRAPH_INSTANCE_SCHEMA = [
	SchemaField('id', 'STRING', mode='required'),
	SchemaField('type', 'STRING', mode='required'),
	SchemaField('properties', 'STRING', mode='nullable'),
	SchemaField('metadata', 'STRING', mode='nullable')
]

DEVICE_INSTANCE_SCHEMA = [
    SchemaField('id', 'STRING', mode='required'),
    SchemaField('parent_id', 'STRING', mode='required'),
    SchemaField('type', 'STRING', mode='nullable'),
    SchemaField('properties', 'STRING', mode='nullable'),
    SchemaField('metadata', 'STRING', mode='nullable')
]

DEVICE_TYPE_SCHEMA = [
    SchemaField('id', 'STRING', mode='required'),
    SchemaField('parent_id', 'STRING', mode='required'),
    SchemaField('state', 'STRING', mode='nullable'),
    SchemaField('properties', 'STRING', mode='nullable'),
    SchemaField('metadata', 'STRING', mode='nullable')
]

#dev_type_id,name,type,message_type_id,properties,state,metadata
DEVICE_PORT_SCHEMA = [
    SchemaField('dev_type_id', 'STRING', mode='required'),
    SchemaField('name', 'STRING', mode='required'),
    SchemaField('type', 'STRING', mode='required'),
    SchemaField('message_type_id', 'STRING', mode='required'),
    SchemaField('properties', 'STRING', mode='nullable'),
    SchemaField('state', 'STRING', mode='nullable'),
    SchemaField('metadata', 'STRING', mode='nullable')
]

#parent,source,target,source_port,target_port,message_type,properties,metadata
EDGE_INSTANCE_SCHEMA = [
    SchemaField('parent_id', 'STRING', mode='required'),
    SchemaField('source', 'STRING', mode='required'),
    SchemaField('target', 'STRING', mode='required'),
    SchemaField('source_port', 'STRING', mode='required'),
    SchemaField('target_port', 'STRING', mode='required'),
    SchemaField('message_type', 'STRING', mode='nullable'),
    SchemaField('properties', 'STRING', mode='nullable'),
    SchemaField('metadata', 'STRING', mode='nullable')
]

# event_id,time,elapsed,dev,rts,seq,L,S,M,port,cancel,fanout,send_event_id,type
EVENT_SCHEMA = [
    SchemaField('event_id', 'STRING', mode='required'),
    SchemaField('time', 'FLOAT', mode='required'),
    SchemaField('elapsed', 'FLOAT', mode='required'),
    SchemaField('dev', 'STRING', mode='required'),
    SchemaField('rts', 'INTEGER', mode='nullable'),
    SchemaField('seq', 'INTEGER', mode='nullable'),
    SchemaField('L', 'STRING', mode='nullable'),
    SchemaField('S', 'STRING', mode='nullable'),
    SchemaField('M', 'STRING', mode='nullable'),
    SchemaField('port', 'STRING', mode='nullable'),
    SchemaField('cancel', 'STRING', mode='nullable'),
    SchemaField('fanout', 'STRING', mode='nullable'),
    SchemaField('send_event_id', 'STRING', mode='nullable'),
    SchemaField('type', 'STRING', mode='required')
]
