from flask_script import Command, Manager, Option
from app import app
from scripts.db_builder import Handler

import time, sys

manager = Manager(app)

class DBSetup(Command):
	option_list = (
		Option('--name', '-n', dest='name'),
		Option('--location', '-l', dest='base'),
		Option('--epoch-granularity', '-g', dest='granularity'),
		Option('--max-epoch', '-e', dest='max_epoch'),
		Option('--nodes-per-part', '-p', dest='nnp')
		)

	def run(self, name, base, granularity, max_epoch, nnp):
		if max_epoch:
			e = int(max_epoch)
		else:
			e = 100

		if granularity:
			g = int(granularity)
		else:
			g = 0

		if base:
			b = base
		else:
			b = "data/"

		if nnp:
			n = int(nnp)
		else:
			n = 50

		if not name:
			print("Graph instance name must be provided with flag: -n [name]")
			return

		db = Handler(name, b, max_epoch = e, granularity = g, nodes_per_part = n)

class Help(Command):
	def run(self):
		print("Usage: manage.py [command] [options]")
		print
		print("Commands:")
		print('{0: <10}{1}'.format('  initdb', "initialise the database"))
		print('{0: <10}{1}'.format('  help', "show this help page"))
		print
		print("Options for initdb:")
		print('{0: <38}{1}'.format('  -n [name], --name [name]', "name of the graph instance file (e.g. 'ising_spin_100x100')"))
		print('{0: <38}{1}'.format('  -l [dir], --location [dir]', "directory where graph instance file is located"))
		print('{0: <38}{1}'.format('  -g [n], --epoch-granularity [n]', "sets number of epochs between snapshots to 10^n (total epochs / 10 recommended)"))
		print('{0: <38}{1}'.format('  -e [n], --max-epoch [n]', "maximum number of epochs to be processed (<100 recommended)"))
		print('{0: <38}{1}'.format('  -p [n], --nodes-per-part [n]', "number of devices in each Metis graph partition (<100 recommended)"))


manager.add_command('initdb', DBSetup())
manager.add_command('help', Help())

if __name__ == "__main__":
    manager.run()
