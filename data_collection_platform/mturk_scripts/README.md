# IGLU-turk-tasks
This repo has turk task descriptions for collecting data

## Architecture
### TODO: Update when complete

`mturk_scripts/`: Scripts that query the MTurk API to create HITs, collect and review responses, and process results.

`qual_tasks/`: qualifications tasks for filtering Turk workers

`evaluation_task/`: part of our microservices RPC system

## Running MTurk Tasks
The following section applies to `mturk_scripts/`.

To run a new Turk job end to end, run `python run_turk_jobs.py`. This starts a basic crowdsourcing pipeline that reads a CSV input file for task specific parameters, creates HITs, collects results when they are ready, and collates the output data with the input parameters.

More information about each file is below.

`input.csv`: The default CSV input file containing parameters for your task. You can specify a different input via command line when running `python create_jobs.py`.

`example.html`: An example Turk task UI. We are using the `ExternalQuestion` framework for Turk task creation. For MTurk to access the task, the content needs to be hosted at a publicly accessible IP.

`external_question.xml`: XML wrapper around the Turk task HTML. This contains the embedded task URL. As an illustration, I have pushed `example.html` to our AWS S3 bucket.

`create_jobs.py`: Creates HITs based on your specifications (reward, description, task URL, etc.). This also creates query parameters that embed the data from `input.csv` and passes it along to the external URL. You can write code in your Turk task to parse the URL query parameters you are expecting to render content dynamically. It also writes job creation parameters to `turk_job_specs.csv`

`get_results.py`: Collects crowdsourced responses. This script checks K times for Turk responses that are in a reviewable state. If there are completed tasks, it parses the XML response and writes answers to a CSV file `turk_output.csv`.

`collate_answers.py`: Collates the input (task specification) and output (Turker responses) dataframes, and outputs a joined CSV ready for postprocessing and downstream uses.

Note that the code is relatively new and written for development purposes. There are some changes that will need to be made for production MTurk tasks, eg. changing the sandbox endpoint, collecting tasks with longer wait times, removing logic to delete outstanding HITs. 

The scripts were adapted from an internal project, and were not written as a general purpose framework. User-specific parameters like access keys have been marked with `TODO` and project specific sections have been highlighted with `NOTE` in comments throughout the files, where applicable. You may also want to extend these templates with custom pre and postprocessing scripts.
