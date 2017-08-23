import sys
import os
import json
import pstats

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
# test gals_heat


if not os.path.isfile('test/results/baseline_node_benchmark.txt'):
# generating test_xmls
	for n in range(10, 100, 10):
		if not os.path.isfile("test/files/nodes/gals_heat_test_{0}_{0}.xml".format(n)):
			os.system("python3 test/tools/create_gals_heat_instance.py {0} > test/files/nodes/gals_heat_test_{0}_{0}.xml".format(n))

	for n in [100, 200, 300, 350]:
		if not os.path.isfile("test/files/nodes/gals_heat_test_{0}_{0}.xml".format(n)):
			os.system("python3 test/tools/create_gals_heat_instance.py {0} > test/files/nodes/gals_heat_test_{0}_{0}.xml".format(n))

	for n in range(10, 100, 10):
		if not os.path.isfile("test/files/nodes/ising_spin_test_{0}_{0}.xml".format(n)):
			os.system("python3 test/tools/create_ising_spin_instance.py {0} > test/files/nodes/ising_spin_test_{0}_{0}.xml".format(n))

	for n in [100, 200, 300, 350]:
		if not os.path.isfile("test/files/nodes/ising_spin_test_{0}_{0}.xml".format(n)):
			os.system("python3 test/tools/create_ising_spin_instance.py {0} > test/files/nodes/ising_spin_test_{0}_{0}.xml".format(n))


	# generating events
	graph_files = []
	for filename in os.listdir('test/files/nodes'):
		last = filename.split("_")[-1]
		ext = filename.split(".")[-1]
		if ext == "xml" and last != "event.xml" and last != "snapshot.xml":
			graph_files.append(filename)

	os.chdir("../")
	for f in graph_files:
		base = f.split(".")[0]
		if not os.path.isfile("proj/test/files/nodes/{0}_event.xml".format(base)):
			os.system("bin/epoch_sim proj/test/files/nodes/{0} --log-events proj/test/files/nodes/{1}_event.xml --max-steps 10 --snapshots 1 proj/test/files/nodes/{1}_snapshot.xml".format(f, base))


	# testing time
	os.chdir("proj/")

	for f in graph_files:
		base = f.split(".")[0]
		if not os.path.isfile("test/profiles/nodes/profile_{0}.cprof".format(base)):
			os.system("python -m cProfile -o test/profiles/nodes/profile_{0}.cprof manage.py initdb --name {0} --location test/files/nodes/".format(base))

	# reading stats
	for filename in os.listdir('test/profiles/nodes'):
		if filename.split(".")[-1] == "cprof":
			base = filename.split(".")[0]
			os.system("python profile_reader.py test/profiles/nodes/{0} > test/profiles/nodes/prof/{1}.txt".format(filename, base))

	benchmarks = {"ising_spin": {}, "gals_heat": {}}

	for filename in os.listdir('test/profiles/nodes/prof'):
		f = open('test/profiles/nodes/prof/' + filename, "r")
		base = filename.split(".")[0]
		graph_name = ""
		nodes = int(base.split("_")[-1]) ** 2
		for word in base.split("_"):
			if word == "test":
				break
			if word != "profile":
				graph_name += word + "_"

		graph_name = graph_name[:-1]

		for line in f: 
			words = line.strip().split(" ")
			if words[-1] == "seconds":
				for i in range(-1, (-1 * len(words)) - 1, -1):
					if is_number(words[i]):
						benchmarks[graph_name][nodes] = float(words[i])
						break

	with open('test/results/baseline_node_benchmark.txt', 'w') as outfile:
	    json.dump(benchmarks, outfile)




# event tests

if not os.path.isfile('test/results/event_benchmark.txt'):
	if not os.path.exists("test/files/events/"):
		os.makedirs("test/files/events/")

	if not os.path.exists("test/profiles/events/"):
		os.makedirs("test/profiles/events/")


	if not os.path.exists("test/profiles/events/prof"):
		os.makedirs("test/profiles/events/prof")

	if not os.path.isfile("test/files/events/gals_heat_test_100_100.xml"):
		os.system("python3 test/tools/create_gals_heat_instance.py {0} > test/files/events/gals_heat_test_{0}_{0}.xml".format(100))
	f = "gals_heat_test_100_100.xml"
	base = "gals_heat_test_100_100"



	os.chdir("../")

	if not os.path.isfile("proj/test/files/events/gals_heat_test_100_100_event.xml"):
		os.system("bin/epoch_sim proj/test/files/events/{0} --log-events proj/test/files/events/{1}_event.xml --max-steps 100 --snapshots 1 proj/test/files/events/{1}_snapshot.xml".format(f, base))


	os.chdir("proj/")

	base = f.split(".")[0]

	for i in range(0, 100, 10):
		if not os.path.isfile("test/profiles/events/profile_{0}_event_{1}.cprof".format(base, i)):
			os.system("python -m cProfile -o test/profiles/events/profile_{0}_event_{1}.cprof manage.py initdb -o y --name {0} --location test/files/events/ -e {1}".format(base, i))


	# reading stats
	for filename in os.listdir('test/profiles/events'):
		if filename.split(".")[-1] == "cprof":
			base = filename.split(".")[0]
			os.system("python profile_reader.py test/profiles/events/{0} > test/profiles/events/prof/{1}.txt".format(filename, base))

	benchmarks = {"ising_spin": {}, "gals_heat": {}}

	for filename in os.listdir('test/profiles/events/prof'):
		f = open('test/profiles/events/prof/' + filename, "r")
		base = filename.split(".")[0]
		graph_name = ""
		events = int(base.split("_")[-1])
		for word in base.split("_"):
			if word == "test":
				break
			if word != "profile":
				graph_name += word + "_"



		graph_name = graph_name[:-1]

		for line in f: 
			words = line.strip().split(" ")
			if words[-1] == "seconds":
				for i in range(-1, (-1 * len(words)) - 1, -1):
					if is_number(words[i]):
						benchmarks[graph_name][events] = float(words[i])
						break

	with open('test/results/event_benchmark.txt', 'w') as outfile:
	    json.dump(benchmarks, outfile)



if not os.path.isfile('test/results/snapshot_granularity_benchmark.txt'):
	if not os.path.exists("test/files/granularity/"):
		os.makedirs("test/files/granularity/")

	if not os.path.exists("test/profiles/granularity/"):
		os.makedirs("test/profiles/granularity/")


	if not os.path.exists("test/profiles/granularity/prof"):
		os.makedirs("test/profiles/granularity/prof")

	if not os.path.isfile("test/files/granularity/gals_heat_test_100_100.xml"):
		os.system("python3 test/tools/create_gals_heat_instance.py {0} > test/files/granularity/gals_heat_test_{0}_{0}.xml".format(100))
	
	f = "gals_heat_test_100_100.xml"
	base = "gals_heat_test_100_100"

	if not os.path.isfile("test/files/granularity/{0}_event.xml".format(base)):
		os.chdir("../")
		os.system("bin/epoch_sim proj/test/files/granularity/{0} --log-events proj/test/files/granularity/{1}_event.xml --max-steps 100 --snapshots 1 proj/test/files/granularity/{1}_snapshot.xml".format(f, base))
		os.chdir("proj/")

	base = f.split(".")[0]

	for i in range(3):
		if not os.path.isfile("test/profiles/granularity/profile_{0}_granularity_{1}.cprof".format(base, i)):
			os.system("python -m cProfile -o test/profiles/granularity/profile_{0}_granularity_{1}.cprof manage.py initdb -o y --name {0} --location test/files/granularity/ -g {1}".format(base, i))


	# reading stats
	for filename in os.listdir('test/profiles/granularity'):
		if filename.split(".")[-1] == "cprof":
			base = filename.split(".")[0]
			os.system("python profile_reader.py test/profiles/granularity/{0} > test/profiles/granularity/prof/{1}.txt".format(filename, base))

	benchmarks = {"gals_heat": {}}

	for filename in os.listdir('test/profiles/granularity/prof'):
		f = open('test/profiles/granularity/prof/' + filename, "r")
		base = filename.split(".")[0]
		graph_name = ""
		granularity = int(base.split("_")[-1])
		for word in base.split("_"):
			if word == "test":
				break
			if word != "profile":
				graph_name += word + "_"



		graph_name = graph_name[:-1]

		for line in f: 
			words = line.strip().split(" ")
			if words[-1] == "seconds":
				for i in range(-1, (-1 * len(words)) - 1, -1):
					if is_number(words[i]):
						benchmarks[graph_name][granularity] = float(words[i])
						break

	with open('test/results/snapshot_granularity_benchmark.txt', 'w') as outfile:
	    json.dump(benchmarks, outfile)



if not os.path.isfile('test/results/partition_benchmark.txt'):
	if not os.path.exists("test/files/partition/"):
		os.makedirs("test/files/partition/")

	if not os.path.exists("test/profiles/partition/"):
		os.makedirs("test/profiles/partition/")


	if not os.path.exists("test/profiles/partition/prof"):
		os.makedirs("test/profiles/partition/prof")

	if not os.path.isfile("test/files/partition/gals_heat_test_100_100.xml"):
		os.system("python3 test/tools/create_gals_heat_instance.py {0} > test/files/partition/gals_heat_test_{0}_{0}.xml".format(100))
	
	f = "gals_heat_test_100_100.xml"
	base = "gals_heat_test_100_100"

	if not os.path.isfile("test/files/partition/{0}_event.xml".format(base)):
		os.chdir("../")
		os.system("bin/epoch_sim proj/test/files/partition/{0} --log-events proj/test/files/partition/{1}_event.xml --max-steps 10 --snapshots 1 proj/test/files/partition/{1}_snapshot.xml".format(f, base))
		os.chdir("proj/")

	base = f.split(".")[0]

	for i in [10, 50, 100, 150]:
		if not os.path.isfile("test/profiles/partition/profile_{0}_granularity_{1}.cprof".format(base, i)):
			os.system("python -m cProfile -o test/profiles/partition/profile_{0}_granularity_{1}.cprof manage.py initdb -o y --name {0} --location test/files/partition/ -p {1}".format(base, i))


	# reading stats
	for filename in os.listdir('test/profiles/partition'):
		if filename.split(".")[-1] == "cprof":
			base = filename.split(".")[0]
			os.system("python profile_reader.py test/profiles/partition/{0} > test/profiles/partition/prof/{1}.txt".format(filename, base))

	benchmarks = {"gals_heat": {}}

	for filename in os.listdir('test/profiles/partition/prof'):
		f = open('test/profiles/partition/prof/' + filename, "r")
		base = filename.split(".")[0]
		graph_name = ""
		partition = int(base.split("_")[-1])
		for word in base.split("_"):
			if word == "test":
				break
			if word != "profile":
				graph_name += word + "_"



		graph_name = graph_name[:-1]

		for line in f: 
			words = line.strip().split(" ")
			if words[-1] == "seconds":
				for i in range(-1, (-1 * len(words)) - 1, -1):
					if is_number(words[i]):
						benchmarks[graph_name][partition] = float(words[i])
						break

	with open('test/results/partition_benchmark.txt', 'w') as outfile:
	    json.dump(benchmarks, outfile)

