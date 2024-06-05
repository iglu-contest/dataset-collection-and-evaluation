
import xmltodict
import boto3
import json
import pandas as pd
import os
import csv
import argparse
import ast
from urllib.parse import quote
from datetime import datetime

# TODO: Replace with your requester sandbox endpoint
# eg. "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
MTURK_SANDBOX = ""
# TODO: Ensure that environment keys are set and have MTurk API access
access_key = os.getenv("AWS_ACCESS_KEY_ID")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

mturk = boto3.client(
    "mturk",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="us-east-1", # TODO: replace with your region!
    endpoint_url=MTURK_SANDBOX,
)
print("I have $" + mturk.get_account_balance()["AvailableBalance"] + " in my Sandbox account")


def create_turk_job(xml_file_path: str, input_csv: str):
    # Delete outstanding HITs before creating new Turk jobs.
    # NOTE: This is for use in development only. Remove in production.
    for item in mturk.list_hits()["HITs"]:
        hit_id = item["HITId"]
        print("HITId:", hit_id)

        # Get HIT status
        status = mturk.get_hit(HITId=hit_id)["HIT"]["HITStatus"]
        print("HITStatus:", status)

        # If HIT is active then set it to expire immediately
        if status == "Assignable" or status == "Reviewable":
            response = mturk.update_expiration_for_hit(HITId=hit_id, ExpireAt=datetime(2015, 1, 1))

        # Delete the HIT
        try:
            mturk.delete_hit(HITId=hit_id)
        except:
            print("Not deleted")
        else:
            print("Deleted")

    # XML file containing ExternalQuestion object.
    # See MTurk API docs for constraints.
    with open(xml_file_path, "r") as fd:
        question = fd.read()

    # Where we will save the turk job parameters
    turk_jobs_df = pd.DataFrame()
    with open(input_csv, newline="") as csvfile:
        turk_inputs = csv.reader(csvfile, delimiter=",")
        headers = next(turk_inputs, None)
        # Construct the URL query params, which are used to populate information for the task.
        # NOTE: this part will be specific to your Turk task
        for row in turk_inputs:
            query_params = ""
            job_spec = {}
            for i in range(len(headers)):
                # skip empty fields
                if not row[i]:
                    continue
                
                value = row[i].replace(" ", "%20")
                query_params += "{}={}&amp;".format(headers[i], value)
                # Save param info to job specs
                # This will be used to collate output data with input job parameters
                job_spec["Input.{}".format(headers[i])] = row[i]
            curr_question = question.format(query_params)

            print(curr_question)

            # TODO: Edit this section with the correct reward, task description, etc.
            new_hit = mturk.create_hit(
                Title="IGLU Task",
                Description="You are assigned the role of either a builder or an architect...",
                Keywords="image, interactive, quick",
                Reward="1.0",
                MaxAssignments=1,
                LifetimeInSeconds=600,
                AssignmentDurationInSeconds=600,
                AutoApprovalDelayInSeconds=14400,
                Question=curr_question,
            )
            print("A new HIT has been created. You can preview it here:")
            print(
                "https://workersandbox.mturk.com/mturk/preview?groupId="
                + new_hit["HIT"]["HITGroupId"]
            )
            print("HITID = " + new_hit["HIT"]["HITId"] + " (Use to Get Results)")
            job_spec["HITId"] = new_hit["HIT"]["HITId"]

            turk_jobs_df = turk_jobs_df.append(job_spec, ignore_index=True)

    turk_jobs_df.to_csv("turk_job_specs.csv", index=False)

    # Remember to modify the URL above when publishing
    # HITs to the live marketplace.
    # Use: https://worker.mturk.com/mturk/preview?groupId=


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--xml_file", 
        description="XML containing static URL hosting Turk task content used for the ExternalQuestion framework", 
        type=str,
        default="external_question.xml"
    )
    parser.add_argument(
        "--input_csv",
        description="Path to input CSV file containing Turk task parameters",
        type=str,
        required=True
    )

    args = parser.parse_args()
    create_turk_job(args.xml_file, args.input_csv)
