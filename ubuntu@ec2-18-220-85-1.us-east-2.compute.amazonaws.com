user acceptance tests
	- expected result based on a set procedure
	- user stories

heatmaps for number of messages received



AIMS
	JULY
	- bigquery querying
	- device view
		- ports
		- circular view
		- messages
	- dynamic zoom
		- graph subsetting with fixed border nodes
		- fast algo to extend
		- messages
	AUGUST
	- benchmarking



19/7/17
	- device view VISUALS


- storing preprocessed aggregate data
- figure out data structure for max speed during user interaction
- cluster megadevice (all edges collapse into one edge) (metis)

design brief document
	- user should be able to...
	- frame rate should be...
	- lag should be...


NEXT STEPS:
	- d3 show aggregates!
	- event incorportation
	- device view + expand ports



OPTIMISATION STEPS
	- SQL subquery from LIMIT ORDER BY to MAX GROUP BY
	- cursor arraysize
	- potential solution: snapshots
	- 


process substition
snapshots

gzip

verify if user selects nodes number

overall design
frontend
backend
evaluation (fps)


TODO:
epoch snapshot browser
start-pause functionality
epoch show-er
script benchmarks