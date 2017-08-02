from app import app
from scripts.db import DBBuilder

import time, sys

start_time = time.time()

assert(len(sys.argv) == 2)
db = DBBuilder(sys.argv[1])

print("******************************************************************************")
print("FINISH (%3f seconds)" % (time.time() - start_time))
print("******************************************************************************")

print("RUNNING SERVER...")
app.run(debug=True)