from flask_script import Command, Manager, Option
from app import app
from scripts.db_builder import DBBuilder

import time, sys

manager = Manager(app)

class DBSetup(Command):
	option_list = (
		Option('--name', '-n', dest='name'),
		Option('--location', '-l', dest='base'),
		Option('--event-num', '-e', dest='events')
		)

	def run(self, name, base = "data/", events = 1000000):
		if base and events:
			db = DBBuilder(name, base, events)
		else:
			db = DBBuilder(name)

manager.add_command('initdb', DBSetup())

if __name__ == "__main__":
    manager.run()
