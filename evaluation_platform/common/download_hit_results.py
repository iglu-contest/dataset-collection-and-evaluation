"""
Script to download the last 100 hit results.
"""
import argparse
from collections import defaultdict
import boto3
import datetime
import dotenv
import json
import os
import sys

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from hit_manager import HITManager  # noqa: E402
from common import utils, logger  # noqa: E402

_LOGGER = logger.get_logger(__name__)


# must have value less than or equal to 100
MAX_RESULTS = 100


def read_args():
    today = datetime.date.today().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser()
    parser.add_argument('--hit_type', type=str, help='Type of hit to retrieve.',
                        default='test-hit')
    parser.add_argument('--config_filepath', type=str, help='Path to file with json config.',
                        default='env_configs.json')
    parser.add_argument('--config', choices=['production', 'sandbox'], default='sandbox',
                        help='Environment to use for operations')
    parser.add_argument('--env_filepath', type=str, default='.env',
                        help='Path to .env file with environment variables AWS_ACCESS_KEY_ID. '
                             'and AWS_SECRET_ACCESS_KEY, in case they are not already set.')
    parser.add_argument('--output_filepath', type=str, default=f'hit_results_{today}.json',
                        help='')
    return parser.parse_args()


def main():
    args = read_args()

    dotenv.load_dotenv(args.env_filepath)

    config = utils.read_config(args.config, config_filepath=args.config_filepath)

    mturk_client = boto3.client(
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', ''),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
        service_name='mturk',
        region_name='us-east-1',
        endpoint_url=config['mturk_endpoint'],
    )

    partial_results = mturk_client.list_hits(MaxResults=MAX_RESULTS)
    complete_results = []

    done = partial_results['NumResults'] == 0
    pagination_token = partial_results['NextToken']
    oldest_hit = datetime.datetime.today()

    assignment_hits = defaultdict(list)

    while not done:
        _LOGGER.info("Processing hits: " + str(partial_results['NumResults']))
        retrieved_hits = partial_results['HITs']
        for hit in retrieved_hits:
            # Get hit assignments, if any
            if not ('RequesterAnnotation' in hit and
                    json.loads(hit['RequesterAnnotation'])['hit_type'] == args.hit_type
                    # and hit['NumberOfAssignmentsCompleted'] + hit['NumberOfAssignmentsPending'] > 0
                ):
                continue

            if oldest_hit > hit['CreationTime'].replace(tzinfo=None):
                oldest_hit = hit['CreationTime'].replace(tzinfo=None)

            assignments = mturk_client.list_assignments_for_hit(HITId=hit['HITId'])
            hit['assignments'] = assignments['Assignments']
            if not datetime.datetime.now().timestamp() >= hit['Expiration'].timestamp():
                assignment_hits['running'].append(hit['HITId'])
            if hit["NumberOfAssignmentsPending"] > 0:
                assignment_hits['pending'].append(hit['HITId'])
            if hit["NumberOfAssignmentsAvailable"] > 0:
                assignment_hits['available'].append(hit['HITId'])
            if hit["NumberOfAssignmentsCompleted"] > 0:
                assignment_hits['completed'].append(hit['HITId'])
            hit.pop('Question')
            complete_results.append(hit)

        partial_results = mturk_client.list_hits(
            MaxResults=MAX_RESULTS, NextToken=pagination_token)
        if 'NextToken' in partial_results:
            pagination_token = partial_results['NextToken']
        else:
            pagination_token = None
        done = partial_results['NumResults'] == 0

    print(
        f'RUNNING HITS {len(assignment_hits["running"])} \n'
        f'Assignments pending: {len(assignment_hits["pending"])} hits {assignment_hits["pending"]} \n'
        f'assignments available: {len(assignment_hits["available"])} hits {assignment_hits["available"]} \n'
        f'assignments completed: {len(assignment_hits["completed"])}'
    )

    _LOGGER.info(f'Hits of correct type with completed or submitted assignments returned '
                 f'{len(complete_results)}')
    _LOGGER.info(f'Oldest HIT {oldest_hit.strftime("%Y-%m-%d")}')

    with open(args.config + args.output_filepath, 'w') as output_file:
        json.dump(complete_results, output_file, default=str, indent=2)


if __name__ == '__main__':
    main()
