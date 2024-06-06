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

from common import utils, logger  # noqa: E402

_LOGGER = logger.get_logger(__name__)


# must have value less than or equal to 100
MAX_RESULTS = 100


def read_args():
    today = datetime.date.today().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker_id', type=str, help='Id of the worker', required=True)
    parser.add_argument('--config_filepath', type=str, help='Path to file with json config.',
                        default='env_configs.json')
    parser.add_argument('--config', choices=['production', 'sandbox'], default='sandbox',
                        help='Environment to use for operations')
    parser.add_argument('--env_filepath', type=str, default='.env',
                        help='Path to .env file with environment variables AWS_ACCESS_KEY_ID. '
                             'and AWS_SECRET_ACCESS_KEY, in case they are not already set.')
    parser.add_argument('--message', type=str, required=True, help='')
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

    message = (
        'Hello!\n\n It appears to be a problem with your HIT submission for the IGLU project. ' +
        args.message.replace('\\n', '\n') +
        '\n\nBest regards,\n\nThe IGLU team'
    )
    _LOGGER.info(f"Sending {message} to {args.worker_id}")
    mturk_client.notify_workers(
        Subject='Problem with your HIT submission: "IGLU - Play Minecraft game!"',
        MessageText=message, WorkerIds=[args.worker_id]
    )


if __name__ == '__main__':
    main()
