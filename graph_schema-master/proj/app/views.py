from app import app
from flask import render_template, url_for
import sqlite3

def get_db_uri(db_name, base_dir = "data/db/"):
	return base_dir + db_name + ".db"

def get_db():
	db = sqlite3.connect(get_db_uri(app.config.get('DATABASE')))
	return db

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

