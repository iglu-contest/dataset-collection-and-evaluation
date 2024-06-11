"""Tests to assert the GridworldTaskToJsonCompleteTaskEncoder works with given jinja template.

To run this test, first you need to set the environment variable TEMPLATE_FILEPATH
with a path to the jinja file that will be used as template.
"""

import json
import os
import itertools
import unittest

from typing import Any, Dict

from gridworld import tasks

MC_MATRIAL_IDs = [
    174,  # GRAY_WOOL
    178,  # BLUE_WOOL
    180,  # GREEN_WOOL
    181,  # RED_WOOL
    168,  # ORANGE_WOOL
    177,  # PURPLE_WOOL
    171,  # YELLOW_WOOL
]


from gridworld_task_to_minecraft_task_encoder import GridworldTaskToMinecraftTaskEncoder


def powerset(d: Dict[str, Any]):
    """Retuns the powerset, i.e., the list of all unique combinations of elements in d."""
    keys = list(d.keys())
    keys_powerset = itertools.chain.from_iterable(
        itertools.combinations(keys, r) for r in range(len(keys) + 1))
    for key_set in list(keys_powerset):
        if len(key_set) == 0:
            continue
        yield {k: d[k] for k in key_set}


class GridworldTaskToJsonCompleteTaskEncoderTest(unittest.TestCase):

    TASK_TEMPLATE_FILEPATH = None

    def setUp(self) -> None:
        self.assertIsNotNone(self.TASK_TEMPLATE_FILEPATH)
        self.architect_role_id = 'architect123'
        self.builder_role_id = 'builder123'

        BLUE = 1
        RED = 0

        chat = 'Hello there\ngeneral Kenobi'
        self.custom_starting_grid = [(0, -1, 0, BLUE), (0, 0, 0, BLUE), (0, 1, 0, BLUE)]
        self.custom_target_grid = self.custom_starting_grid + [
            (1, -1, 0, RED), (1, 0, 0, RED), (1, 1, 0, RED), (1, 2, 0, RED)]
        self.custom_task = tasks.Task(
            chat=chat,
            target_grid=tasks.Tasks.to_dense(self.custom_target_grid),
            last_instruction='general Kenobi',
            starting_grid=self.custom_starting_grid,
            full_grid=tasks.Tasks.to_dense(self.custom_target_grid),
        )
        return super().setUp()

    def test_encode_complete_parameters(self):
        """Convert a task with values for all fields.

        This test only needs to finish without failure."""

        gridtask_encoder = GridworldTaskToMinecraftTaskEncoder(
            self.architect_role_id, self.builder_role_id, self.TASK_TEMPLATE_FILEPATH)

        optional_parameters = {
            'world_size_x': 180,
            'world_size_z': 180,
            'game_limit_max_duration_seconds': 15*60,
            'game_limit_max_turns': 3,
            'turn_limits': {
                self.builder_role_id: 3,
                self.architect_role_id: 4,
            },
        }

        json_task = gridtask_encoder.convert(
            task_name='task1',
            task_state='Published',
            task=self.custom_task,
            **optional_parameters,
        )

        # consider all utterances but the last one, which is the last_instruction that should
        # have been removed
        for utterance in self.custom_task.chat.split("\n")[:-1]:
            self.assertIn(utterance, json_task)

        self.assertNotIn(self.custom_task.last_instruction, json_task)

        for key, parameter_value in optional_parameters.items():
            if key != 'turn_limits':
                self.assertIn(str(parameter_value), json_task,
                              msg=f"Parameter {parameter_value} not found in task json")

    def test_encode_incomplete_optional_parameters(self):
        """Convert a task with values for all fields.

        This test only needs to finish without failure."""

        gridtask_encoder = GridworldTaskToMinecraftTaskEncoder(
            self.architect_role_id, self.builder_role_id, self.TASK_TEMPLATE_FILEPATH)

        optional_parameters = {
            'world_size_x': 180,
            'world_size_z': 180,
            'game_limit_max_duration_seconds': 15*60,
            'game_limit_max_turns': 3,
            'turn_limits': {
                self.builder_role_id: 3,
                self.architect_role_id: 4,
            },
        }

        # leave one out parameter
        for parameters_subset in powerset(optional_parameters):

            json_task = gridtask_encoder.convert(
                task_name='task1',
                task_state='Published',
                task=self.custom_task,
                **parameters_subset,
            )

            for key, parameter_value in parameters_subset.items():
                if key != 'turn_limits':
                    self.assertIn(str(parameter_value), json_task,
                                msg=f"Parameter {parameter_value} not found in task json")

            # Correct json format
            try:
                json.loads(json_task)
            except json.decoder.JSONDecodeError as e:
                print("Error encoding task with only optional parameters " +
                      " ".join(parameters_subset.keys()))
                raise(e)


if __name__ == '__main__':
    template_filepath = os.environ.get(
        'TASK_TEMPLATE_FILEPATH',
        'minecraft_task_template.json.j2')
    GridworldTaskToJsonCompleteTaskEncoderTest.TASK_TEMPLATE_FILEPATH = template_filepath
    unittest.main()