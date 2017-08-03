from app import app
from flask import render_template, url_for
import sqlite3

def get_db_uri(db_name, base_dir = "data/db/"):
	return base_dir + db_name + ".db"

def get_db():
	db = sqlite3.connect(get_db_uri(app.config.get('DATABASE')))
	return db

def execute_query(query, args=()):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return rows

@app.teardown_appcontext
def close_connection(exception):
	db = None
	if app.config.get('DATABASE'):
		db = sqlite3.connect(get_db_uri(app.config.get('DATABASE')))

	if db:
		db.close()
		db = None


@app.route('/')
@app.route('/index')
def index():
    return render_template("graph.html")

@app.route("/db")
def db():
	cur = get_db().cursor()
	cur.execute("""SELECT * FROM device_states""")
	rows = cur.fetchall()
	return '<br>'.join(str(row) for row in rows)


@app.route("/graph/<part_id>")
def graph(part_id):
	if part_id == "base":
		level = 0
	else:
		level = len(part_id.split("_")) - 2

	nlevels = execute_query("SELECT max FROM levels")

	if level < nlevels[0][0] - 2:
		nodes = execute_query("SELECT partition_{} FROM device_partitions WHERE partition_{} = ?".format(level + 1, level),
							[part_id])
	else:
		nodes = execute_query("SELECT id FROM device_partitions WHERE partition_{} = ?".format(level),
							[part_id])
	
	return '<br>'.join(str(row) for row in nodes)