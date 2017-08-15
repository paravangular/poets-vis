from app import app
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
    