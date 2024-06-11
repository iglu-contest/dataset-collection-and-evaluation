"""Convert a set of hardcoded tasks from iglu singleturn dataset in gridworld format.

Two copies of each task will be stored, one with the original starting grid and
one with an empty starting grid.
"""

import argparse
import json
import os
from collections import namedtuple

from gridworld.data import SingleTurnIGLUDataset
from gridworld.tasks import Task, Tasks
from gridworld_task_to_minecraft_task_encoder import GridworldTaskToMinecraftTaskEncoder

TaskAttributes = namedtuple("TaskAttributes", ["task_id", "session_id", "reference_name"])


# TODO this could be passed as a configuration or command line, but this works for now
TASKS_TO_CONVERT = [
    TaskAttributes('2-c135/step-4', 3, ''),
    TaskAttributes('10-c97/step-8', 6, ''),
    TaskAttributes('2-c135/step-4', 2, ''),
    TaskAttributes('4-c92/step-22', 1, ''),
    TaskAttributes('23-c136/step-14', 1, ''),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Convert a set of hardcoded tasks from iglu singleturn dataset in gridworld format.\n'
            'Two copies of each task will be stored, one with the original starting grid and '
            'one with an empty starting grid.'
        )
    )
    parser.add_argument(
        '--output_dirpath',
        help='Path to directory to store generates tasks. If None, current directory'
        'will be used',
        default=None)
    # TODO this is passed as a parameter here to force users to double check
    # the player ids are correct.
    parser.add_argument(
        '--builder_role_id',
        help='Id of the builder role of the particular tournament where this'
             'task will be uploaded to.',
        required=True)
    parser.add_argument(
        '--architect_role_id',
        help='Id of the architect role of the particular tournament where this'
             'task will be uploaded to.',
        required=True)
    parser.add_argument(
        '--task_template_filepath',
        help='Path to the jinja template to render',
        default='--task_template_filepath')
    return parser.parse_args()


def build_task_name(task: TaskAttributes, empty_starting_grid=False) -> str:
    prefix = ''
    if task.reference_name is not None and len(task.reference_name) > 0:
        prefix = f'{task.reference_name}: '
    name = f'{prefix}{task.task_id}-{task.session_id}'.replace('/', '-')
    if empty_starting_grid:
        name += '-empty-start'
    return name


# The purpose of this function is mainly validating the format, but since the
# decoding is done, it's easy to re-encode and improve the format of the string.
def validate_json(task_name, json_str):
    try:
        return json.dumps(json.loads(json_str), indent=2)
    except ValueError as e:
        print(f'{task_name} was not serialized with a correct json format.')
        raise e


def encode_task(
    task_name: str,
    task: Task,
    task_encoder: GridworldTaskToMinecraftTaskEncoder,
    output_dirpath: str
) -> None:

    minecraft_task_json: str = task_encoder.convert(
        task_state='Published',
        task_name=task_name,
        task=task,
    )

    minecraft_task_json = validate_json(task_name, minecraft_task_json)

    output_filepath = os.path.join(output_dirpath, task_name + '.json')
    with open(output_filepath, 'w') as task_file:
        task_file.write(minecraft_task_json)


def main():
    args = parse_args()

    task_encoder = GridworldTaskToMinecraftTaskEncoder(
        args.architect_role_id, args.builder_role_id, args.task_template_filepath)

    output_dirpath = args.output_dirpath if args.output_dirpath is not None else '.'
    os.makedirs(output_dirpath, exist_ok=True)

    iglu_dataset = SingleTurnIGLUDataset()
    for task in TASKS_TO_CONVERT:
        task_name = build_task_name(task, empty_starting_grid=False)
        iglu_task = iglu_dataset.tasks[task.task_id][task.session_id]
        print('Converting task: ', task_name)
        # Encode original task
        try:
            encode_task(task_name, iglu_task, task_encoder, output_dirpath)
        except ValueError:
            pass  # If the exception is raised, it will print the appropriate message.

        # Encode task with empty grid
        empty_start_iglu_task = Task(
            chat='',
            target_grid=iglu_task.target_grid,
            last_instruction='',
            starting_grid=[],
            full_grid=iglu_task.target_grid,
        )
        task_name = build_task_name(task, empty_starting_grid=True)
        encode_task(task_name, empty_start_iglu_task, task_encoder, output_dirpath)


if __name__ == '__main__':
    main()
