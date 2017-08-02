# Imports the Google Cloud client library
from google.cloud import bigquery
from google.oauth2 import service_account
import schemas
import time
import os
import uuid
import json
from pprint import pprint

import cloudstorage as gcs
from google.appengine.api import app_identity
from controller import make_json

PROJECT = 'poets-172210'

class BigQueryHandler():
    def __init__(self, dataset_name):
        credentials = service_account.Credentials.from_service_account_file('./keys/service-account.json')
        self.client = bigquery.Client(project = PROJECT, credentials=credentials)
        self.dataset_name = dataset_name
        self.dataset = self.find_dataset(dataset_name)

    def get_whole_graph(self):
        graph = {"nodes": {}, "edges": [], "events": []}
        devices = ('SELECT * FROM device_instances')
        edges = ('SELECT * FROM edge_instances')
        events = ('SELECT * FROM events')
        device_query = self.client.run_sync_query(devices)
        device_query.timeout_ms = TIMEOUT_MS
        device_query.run()

        for d in device_query.rows:
            for i in range(schemas.DEVICE_INSTANCE_SCHEMA):
                graph.nodes[d.f[0].v][schemas.DEVICE_INSTANCE_SCHEMA[i].name] = d.f[i].v

        for e in edge_query.rows:
            edge = {}
            for i in range(schemas.EDGE_INSTANCE_SCHEMA):
                edge[schemas.EDGE_INSTANCE_SCHEMA[i].name] = e.f[i].v
            graph.edges.append(edge)

        for e in event_query.rows:
            event = {}
            for i in range(schemas.event_INSTANCE_SCHEMA):
                event[schemas.event_INSTANCE_SCHEMA[i].name] = e.f[i].v
            graph.events.append(event)


class BigQueryLoader():
    def __init__(self, dataset_name, stream_builder):
        credentials = service_account.Credentials.from_service_account_file('./keys/service-account.json')
        self.client = bigquery.Client(project = PROJECT, credentials=credentials)
        self.dataset_name = dataset_name
        self.dataset = self.find_dataset(dataset_name)
        self.stream_builder = stream_builder

        print('Dataset {} created.'.format(self.dataset.name))
        self.create_tables()
        self.stream_all_data()

    def find_dataset(self, dataset_name):
        for dataset in self.client.list_datasets():
            if dataset_name == dataset.name:
                return dataset

        return self.create_dataset(dataset_name)

    def create_dataset(self, dataset_name):
        dataset = self.client.dataset(dataset_name)
        dataset.create()

        return dataset

    def create_tables(self):
        self.create_table('graph_instances', schemas.GRAPH_INSTANCE_SCHEMA)
        self.create_table('device_instances', schemas.DEVICE_INSTANCE_SCHEMA)
        self.create_table('device_types', schemas.DEVICE_TYPE_SCHEMA)
        self.create_table('device_ports', schemas.DEVICE_PORT_SCHEMA)
        self.create_table('edge_instances', schemas.EDGE_INSTANCE_SCHEMA)
        self.create_table('events', schemas.EVENT_SCHEMA)


    def create_table(self, table_name, schema):
        if not self.dataset.table(table_name).exists():
            table = self.dataset.table(table_name, schema)
            table.create()
        else:
            print('Table {} already exists.'.format(table_name))

    def stream_all_data(self):
        self.stream_data('graph_instances',  self.stream_builder.graph_instance_json())
        self.stream_data('device_instances', self.stream_builder.dev_instance_json())

        dev = self.stream_builder.dev_json()
        dev_types = dev["type"]
        dev_ports = dev["port"]

        self.stream_data('device_types', dev_types)
        self.stream_data('device_ports', dev_ports)
        self.stream_data('edge_instances', self.stream_builder.edge_instance_json())
        self.stream_data('events', self.stream_builder.event_json())


    def stream_data(self, table_name, json_data):
        table = self.dataset.table(table_name)
        # Reload the table to get the schema.
        table.reload()

        count = 0
        for row in json_data["rows"]:
            errors = table.insert_data(row)
            count += 1

        if not errors:
            print('Loaded {} row into {}:{}'.format(count, self.dataset_name, table_name))
        else:
            print('Errors:')
            pprint(errors)

    def load_all_data(self):
        self.load_data('graph_instances', 'graph_instances.csv')
        self.load_data('device_instances', 'device_instances.csv')
        self.load_data('device_types', 'device_types.csv')
        self.load_data('device_ports', 'device_ports.csv')
        self.load_data('edge_instances', 'edge_instances.csv')
        self.load_data('events', 'events.csv')

    def load_data(self, table_name, source):
        if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
            self.load_data_from_storage(table_name, source)
        else:
            self.load_data_from_file(table_name, source)


    def load_data_from_file(self, table_name, source):
        table = self.dataset.table(table_name)
        table.reload()

        with open(source, 'rb') as source_file:
            job = table.upload_from_file(
                source_file, source_format='text/csv', skip_leading_rows=1, field_delimiter="|")

        self.wait_for_job(job)

        print('Loaded {} rows into {}:{}.'.format(
            job.output_rows, self.dataset_name, table_name))

    def load_data_from_storage(self, table_name, source):
        # dev environment source uri differs from prod environment
        source = 'gs://' + os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name()) + '/' + source
        table = self.dataset.table(table_name)
        table.reload()
        job_name = str(uuid.uuid4())
        job = self.client.load_table_from_storage(job_name, table, source)

        job.begin()
        self.wait_for_job(job)

        print('Loaded {} rows into {}:{}.'.format(job.output_rows, self.dataset_name, table_name))


    def wait_for_job(self, job):
        while True:
            job.reload()
            if job.state == 'DONE':
                if job.error_result:
                    raise RuntimeError(job.errors)
                return
            time.sleep(1)



