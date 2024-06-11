"""Takes the files with the mappings from task names, agent ids and join codes and returns
a single json file with structure:

{
    <task_name>: {
        "join_code": <join_code>,
        "task_id": <minecraft_task_id>,
    }
}
"""

import argparse
from collections import defaultdict
import json
import os
import sys
from typing import Dict, Any

# Mturk scripts project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
# Minecraft project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from common import logger

_LOGGER = logger.get_logger(__name__)


def read_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
       '--task_id_mapping',
       help='Json file with mapping from task name to task id',
       type=str, required=True,
    )

    parser.add_argument(
       '--join_codes_filepath',
       help='Path to file with the mapping from task names to join codes.',
       type=str, required=True,
    )

    parser.add_argument(
       '--output_codes_filepath',
       help='Path to store the resulting map form task_name to join code. '
            'If None, the same directory as join_codes_filepath will be used.',
       type=str, default=None,
    )

    return parser.parse_args()


def convert_task_names_to_keys(task_mapping):
    result = {}
    for task_map in task_mapping['taskIdNamesList']:
        if task_map['name'] in result:
            _LOGGER.warning(f'Duplicate task name {task_map["name"]}')
        result[task_map['name']] = task_map['id']
    return result


def generate_code(task_id, tournament_id, challenge_id, role_id):
    return '/plaiground:join-task-with-agent ' + ':'.join(
        [tournament_id, challenge_id, task_id])


def main():
    args = read_args()
    with open(args.task_id_mapping, 'r') as task_id_mapping_file:
        task_mapping = json.load(task_id_mapping_file)

    # Add minecraft task id
    task_mapping = convert_task_names_to_keys(task_mapping)

    _LOGGER.info(f'Loaded tasks: {len(task_mapping)}')

    with open(args.join_codes_filepath, 'r') as join_code_mappings_file:
        join_code_mappings = json.load(join_code_mappings_file)

    join_codes = defaultdict(dict)
    shared_code_params = {
        'tournament_id': join_code_mappings['info']['tournamentId'],
        'challenge_id': join_code_mappings['info']['challengeId'],
        'role_id': join_code_mappings['info']['roleId'],
    }
    for task_name, task_id in task_mapping.items():
        join_codes[task_name] = {
            'task_join_code': generate_code(task_id=task_id, **shared_code_params),
            'task_id': task_id
        }

    _LOGGER.info(
        f'Total join codes available: ' +
        str(sum([len(agent_codes_map) for agent_codes_map in join_codes.values()])) +
        f' out of {len(task_mapping)} tasks and {len(join_code_mappings["info"]["agents"])} agents'
    )

    if args.output_codes_filepath is None:
        join_codes_filepath = os.path.join(os.path.dirname(args.join_codes_filepath),
                                           'processed_join_codes.json')
    else:
        join_codes_filepath = args.output_codes_filepath
    with open(join_codes_filepath, 'w') as join_codes_file:
        json.dump(join_codes, join_codes_file)


if __name__ == '__main__':
    main()
