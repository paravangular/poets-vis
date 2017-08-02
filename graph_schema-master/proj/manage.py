from flask_script import Command, Manager, Option
from app import app
from scripts.db import DBBuilder

import time, sys

manager = Manager(app)

class CreateDB(Command):
	option_list = (
		Option('--name', '-n', dest='name'),
		)

	def run(self, name):
		db = DBBuilder(name)

manager.add_command('db', CreateDB())

if __name__ == "__main__":
    manager.run()
