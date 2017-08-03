from app import app
from flask import render_template, url_for
import sqlite3

from scripts.csv_builder import CSVBuilder
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
@app.route('/index')
def index():
    return render_template("graph.html")

@app.route("/db")
def db():
	cur = helper.get_db().cursor()
	cur.execute("""SELECT * FROM device_states""")
	rows = cur.fetchall()
	return '<br>'.join(str(row) for row in rows)


@app.route("/graph/<part_id>")
def graph(part_id):
	csv = CSVBuilder(part_id)
	return '<br />'.join(csv.get())