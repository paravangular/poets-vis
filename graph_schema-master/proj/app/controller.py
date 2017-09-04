from app import app
from flask import render_template, url_for, request, jsonify, redirect, g
import sqlite3

import json

from scripts.json_builder import *
from scripts import helper

from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()

@app.teardown_appcontext
def close_connection(exception):
    db = None
    if app.config.get('DATABASE'):
        db = sqlite3.connect(helper.get_db_uri(app.config.get('DATABASE')))

    if db:
        db.close()
        db = None

@app.before_first_request
def before_first_request():
    meta_prop = cache.get('meta_prop')
    if meta_prop is None:
        cache.set('meta_prop', MetaBuilder(), 0)

@app.route('/')
@app.route('/graph')
def index():
    return redirect("/graph/base", code=302)

@app.route("/graph/<part_id>")
def graph(part_id):
    meta_prop = cache.get('meta_prop')
    builder = cache.get(part_id)
    if builder is None:
        builder = JSONBuilder(part_id)

    return render_template("graph.html", max_level = meta_prop.max_level, state_ranges = meta_prop.ranges_json, 
                device_types = meta_prop.dev_json, data = builder.json, parent = part_id, 
                max_time = meta_prop.max_time, ports = meta_prop.ports, message_types = meta_prop.message_types)

@app.route("/preload_partition", methods=['GET'])
def preload_partition():
    part_id = request.args.get('part_id', "", type=str)
    builder = JSONBuilder(part_id)
    cache.set(part_id, builder, timeout = 60 * 10)
    return ('', 204) # no content

@app.route('/snapshot', methods=['GET'])
def snapshot():
    start = request.args.get('start', 0, type=float)
    end = request.args.get('end', 0, type=float)
    part_id = request.args.get('part_id', "", type=str)
    builder = SnapshotJSONBuilder(start, end, part_id)
    return jsonify(builder.json)


@app.route('/events', methods=['GET'])
def events():
    start = request.args.get('start', 0, type=float)
    end = request.args.get('end', 0, type=float)
    part_id = request.args.get('part_id', "", type=str)
    builder = EventJSONBuilder(start, end, part_id)

    return jsonify(builder.json)


@app.route('/stepper', methods=['GET'])
def stepper():
    part_id = request.args.get('part_id', "", type=str)
    max_level = request.args.get('max_level', 0, type=int)
    builder = StepperJSONBuilder(part_id, max_level)

    return jsonify(builder.json)

@app.route("/device/<dev_id>")
def device(dev_id):
    return render_template("device.html")