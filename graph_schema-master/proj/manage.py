from flask_script import Command, Manager, Option
from app import app
from scripts.db_builder import Handler

import time, sys

manager = Manager(app)

class DBSetup(Command):
	option_list = (
		Option('--name', '-n', dest='name'),
		Option('--location', '-l', dest='base'),
		Option('--granularity', '-g', dest='granularity'),
		Option('--max-epoch', '-e', dest='max_epoch')
		)

	def run(self, name, base, granularity, max_epoch):
		if max_epoch:
			e = max_epoch
		else:
			e = 100

		if granularity:
			g = granularity
		else:
			g = 0

		if base:
			b = base
		else:
			b = "data/"

		db = Handler(name, b, max_epoch = e, granularity = g)

manager.add_command('initdb', DBSetup())

if __name__ == "__main__":
    manager.run()
