import subprocess
import time
import sys

"""
Kicks off a basic MTurk pipeline that schedules Turk tasks, collects results in batches and collates data.

1. Read in CSV containing Turk task parameters.
2. Create HITs using task parameters.
3. Continuously check for completed assignments, fetching results in batches.
4. Collate turk output data with the input job specs.
"""

# TODO: run any preprocessing scripts that construct the input CSV for Turk tasks

# Load input commands and create a separate HIT for each row
# TODO: edit the XML and input CSV parameters as necessary
rc = subprocess.call(["python create_jobs.py --xml_file external_question.xml --input_csv input.csv"], shell=True)
if rc != 0:
    print("Error creating HIT jobs. Exiting.")
    sys.exit()
# Wait for results to be ready
print("Turk jobs created at : %s \n Waiting for results..." % time.ctime())

# TODO: edit the wait time before first response check
time.sleep(100)
# Check if results are ready
rc = subprocess.call(["python get_results.py"], shell=True)
if rc != 0:
    print("Error fetching HIT results. Exiting.")
    sys.exit()

# Collate datasets
print("*** Collating turk outputs and input job specs ***")
rc = subprocess.call(["python collate_answers.py"], shell=True)
if rc != 0:
    print("Error collating answers. Exiting.")
    sys.exit()

# TODO: insert any postprocessing here