from app import app
from flask import render_template, url_for, request, jsonify, redirect
import sqlite3

import json

from scripts.json_builder import *
from scripts import helper

@app.teardown_appcontext
def close_connection(exception):
	db = None
	if app.config.get('DATABASE'):
		db = sqlite3.connect(helper.get_db_uri(app.config.get('DATABASE')))

	if db:
		db.close()
		db = None


@app.route('/')
@app.route('/graph')
def index():
    return redirect("/graph/base", code=302)

@app.route("/graph/<part_id>")
def graph(part_id):
	builder = JSONBuilder(part_id)
	return render_template("graph.html", max_level = builder.max_level, state_ranges = builder.ranges_json, device_types = builder.dev_json, data = builder.json, parent = part_id, max_time = builder.max_time, ports = builder.ports, message_types = builder.message_types)

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


@app.route("/device/<dev_id>")
def device(dev_id):
	return render_template("device.html")