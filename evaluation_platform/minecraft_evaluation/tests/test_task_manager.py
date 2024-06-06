from collections import defaultdict
import itertools
import math
import os
import random
import sys
import unittest

from copy import deepcopy
from itertools import product

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from minecraft_evaluation.task_management.task_manager import TaskManager

TEST_TASKS_FILENAME = 'TEST_TASKS_FILENAME'
TEST_TASKS = {
    "task1": {
        "task_id": "task1_id",
        "task_join_code": "task1_join_code"
    },
    "task2": {
        "task_id": "task2_id",
        "task_join_code": "task2_join_code"
    },
    "task3": {
        "task_id": "task3_id",
        "task_join_code": "task3_join_code"
    }
}

TEST_AGENTS_FILENAME = 'TEST_AGENTS_FILENAME'
TEST_AGENTS = {
    "agent1": [{
        "agent_instance_id": "agent1_instance1_id",
        "agent_instance_name": "agent1_instance1",
    }, {
        "agent_instance_id": "agent1_instance2_id",
        "agent_instance_name": "agent1_instance2",
    }],
    "agent2": [{
        "agent_instance_id": "agent2_instance1_id",
        "agent_instance_name": "agent2_instance1",
    }],
    "agent3": [{
        "agent_instance_id": "agent3_instance1_id",
        "agent_instance_name": "agent3_instance1",
    }],
    "agent4": [{
        "agent_instance_id": "agent4_instance1_id",
        "agent_instance_name": "agent4_instance1",
    }, {
        "agent_instance_id": "agent4_instance2_id",
        "agent_instance_name": "agent4_instance2",
    }, {
        "agent_instance_id": "agent4_instance3_id",
        "agent_instance_name": "agent4_instance3",
    }],
}


class TaskManagerMock(TaskManager):

    @staticmethod
    def read_json_file(json_filepath):
        """Mock that returns constant value instead of content of `agent_info_filepath`."""
        if json_filepath == TEST_TASKS_FILENAME:
            return deepcopy(TEST_TASKS)
        elif json_filepath == TEST_AGENTS_FILENAME:
            return deepcopy(TEST_AGENTS)
        raise ValueError(f'Incorrect filepath for TaskManagerMock: {json_filepath}')


class TaskManagerTest(unittest.TestCase):

    def test_get_codes_once(self):
        """Test single code.

        * Agent and task are valid
        * All codes correspond to the same task
        * Agent instance is no longer available
        * Agent is available only if has more than one instance
        """
        agent_combination_size = 2
        task_manager = TaskManagerMock(
            TEST_TASKS_FILENAME, TEST_AGENTS_FILENAME, agent_combination_size=2)
        join_codes = task_manager.get_next_join_codes()
        self.assertIsNotNone(join_codes)
        self.assertEqual(agent_combination_size, len(join_codes))

        selected_task = join_codes[0].task_name
        seen_agents = set()
        for join_code in join_codes:
            agent_name = join_code.agent_name
            self.assertEqual(selected_task, join_code.task_name,
                             msg='Task name for join codes is not always the same')
            self.assertIn(join_code.task_name, TEST_TASKS,
                          msg='Join code returns invalid task name')
            self.assertIn(agent_name, TEST_AGENTS,
                          msg='Join code returns invalid agent name')
            self.assertTrue(
                task_manager.is_instance_in_use(agent_name, join_code.agent_instance_id),
                msg=f'Join code instance {join_code.agent_instance_id} for agent '
                    f'{agent_name} is still marked as free.')

            # No agent should have been repeated given the number of codes retrieved
            self.assertNotIn(agent_name, seen_agents, msg='Join code has repeated agent')
            seen_agents.add(agent_name)

            # Agent should be available only if it had more than one instance
            if len(TEST_AGENTS[agent_name]) == 1:
                self.assertFalse(
                    task_manager.is_agent_available(agent_name),
                    msg=f'Agent {agent_name} is available after retrieving one join code, '
                        'but has only one instance.')
                self.assertNotIn(
                    agent_name, task_manager.get_available_agents(),
                    msg=f'Agent {agent_name} is returned as available after '
                        'retrieving one join code, but has only one instance.')
            else:
                self.assertTrue(
                    task_manager.is_agent_available(agent_name),
                    msg=f'Agent {agent_name} is not available after retrieving one join code '
                        'but has more than one instance.')
                self.assertIn(
                    agent_name, task_manager.get_available_agents(),
                    msg=f'Agent {agent_name} is not returned as available after '
                        'retrieving one join code, but has more than one instance.')

    def test_get_code_multiple_times(self):
        """Test retrieved codes when asking multiple times, but less than total available.

        * All selected instances are in use
        * No instance is selected twice
        * There is still at least one agent available
        * A task is not returned again for the same agent combination unless all previous task
            were previously used.
        """
        agent_combination_size = 3
        task_manager = TaskManagerMock(
            TEST_TASKS_FILENAME, TEST_AGENTS_FILENAME, agent_combination_size)

        seen_tasks_for_agent_combination = defaultdict(set)
        seen_agent_instances = set()
        while len(task_manager.get_available_agents()) > agent_combination_size:
            join_codes = task_manager.get_next_join_codes()
            self.assertIsNotNone(join_codes)
            self.assertEqual(agent_combination_size, len(join_codes))

            selected_task = join_codes[0].task_name
            agent_combination = []
            for join_code in join_codes:
                self.assertEqual(selected_task, join_code.task_name,
                                msg='Task name for join codes is not always the same')
                agent_name = join_code.agent_name
                self.assertTrue(
                    task_manager.is_instance_in_use(agent_name, join_code.agent_instance_id),
                    msg=f'Join code instance {join_code.agent_instance_id} for agent '
                        f'{agent_name} is still marked as free.')
                # No agent instance should have been repeated
                self.assertNotIn(
                    join_code.agent_instance_id, seen_agent_instances,
                    msg='Join code has repeated agent instance')
                seen_agent_instances.add(join_code.agent_instance_id)
                agent_combination.append(agent_name)

            agent_combination = tuple(agent_combination)
            if len(seen_tasks_for_agent_combination[agent_combination]) < len(TEST_TASKS):
                # This agent combination has not been used for all tasks. Previous tasks
                # should have a lower priority and should not have been retrieved.
                self.assertNotIn(
                    selected_task, seen_tasks_for_agent_combination[agent_combination],
                    msg='A task has been repeated for an agent combination before returning all '
                        'other tasks.')
            seen_tasks_for_agent_combination[agent_combination].add(selected_task)

    def test_get_code_until_no_more_instances_free(self):
        """Test retrieved codes when asking multiple times, until no more instances are free.

        * There is less than `agent_combination_size` available agents.
        * No instance is selected twice.
        * An agent combination is not selected again unless none of the other possible combination
            has at least one agent available.
        * A task is not returned again for the same agent combination unless all previous task
            were previously used.
        """
        agent_combination_size = 1
        task_manager = TaskManagerMock(
            TEST_TASKS_FILENAME, TEST_AGENTS_FILENAME, agent_combination_size)

        seen_tasks_for_agent_combination = defaultdict(set)
        seen_agent_instances = set()

        agent_combination_used_times = {
            agent_combination: 0
            for agent_combination in itertools.combinations(
                TEST_AGENTS.keys(), agent_combination_size)
        }

        # Calculate how many join codes can be retrieved before exceeding instance combinations
        all_instances = [
            agent_instance_info
            for agent_instances in TEST_AGENTS.values() for agent_instance_info in agent_instances
        ]
        max_possible_join_codes = len(
            [1 for _ in itertools.combinations(all_instances, agent_combination_size)])
        total_seen_code_sets = 0
        while total_seen_code_sets <= max_possible_join_codes:
            total_seen_code_sets += 1
            join_codes = task_manager.get_next_join_codes()
            if join_codes is None:
                break

            self.assertEqual(agent_combination_size, len(join_codes))

            selected_task = join_codes[0].task_name
            agent_combination = []
            for join_code in join_codes:
                self.assertEqual(selected_task, join_code.task_name,
                                msg='Task name for join codes is not always the same')
                agent_name = join_code.agent_name
                self.assertTrue(
                    task_manager.is_instance_in_use(agent_name, join_code.agent_instance_id),
                    msg=f'Join code instance {join_code.agent_instance_id} for agent '
                        f'{agent_name} is still marked as free.')
                # No agent instance should have been repeated
                self.assertNotIn(
                    join_code.agent_instance_id, seen_agent_instances,
                    msg='Join code has repeated agent instance')
                seen_agent_instances.add(join_code.agent_instance_id)
                agent_combination.append(agent_name)

            agent_combination = tuple(agent_combination)

            # Test task priority
            if len(seen_tasks_for_agent_combination[agent_combination]) < len(TEST_TASKS):
                # This agent combination has not been used for all tasks. Previous tasks
                # should have a lower priority and should not have been retrieved.
                self.assertNotIn(
                    selected_task, seen_tasks_for_agent_combination[agent_combination],
                    msg='A task has been repeated for an agent combination before returning all '
                        'other tasks.')
            seen_tasks_for_agent_combination[agent_combination].add(selected_task)

            # Test agent combination priority
            other_available_agents = task_manager.get_available_agents()
            if agent_combination_used_times[agent_combination] == 1:
                # Check all previous tasks have been used at least once
                for other_combination, used_times in agent_combination_used_times.items():
                    if set(other_combination) == set(agent_combination):
                        continue
                    if not set(other_combination).issubset(other_available_agents):
                        continue
                    # The combination is available. It should have been used at least once,
                    # otherwise it should have higher priority than selected combination
                    self.assertGreaterEqual(
                        used_times, 1,
                        msg=f'Agent combination {agent_combination} has been used twice before '
                            f'unused and available combination {other_combination}.')

            agent_combination_used_times[agent_combination] += 1

        self.assertLess(
            len(task_manager.get_available_agents()), agent_combination_size,
            msg='No join code was returned, but there are enough agents for a new combination.'
        )

    def test_get_code_after_completing_join_code(self):
        """Test instances are reused after completing a join code.

        Join codes are requested until None is returned. Then, `agent_combination_size` join codes
        are marked as completed. A new join code has to be retrieved next, because there should
        be enough free instances.
        """
        agent_combination_size = 3
        task_manager = TaskManagerMock(
            TEST_TASKS_FILENAME, TEST_AGENTS_FILENAME, agent_combination_size)

        # Calculate how many join codes can be retrieved before exceeding instance combinations
        all_instances = [
            agent_instance_info
            for agent_instances in TEST_AGENTS.values() for agent_instance_info in agent_instances
        ]
        max_possible_join_codes = len(
            [1 for _ in itertools.combinations(all_instances, agent_combination_size)])
        previous_join_codes_sets = []
        join_codes = None
        while len(previous_join_codes_sets) <= max_possible_join_codes:
            join_codes = task_manager.get_next_join_codes()
            if join_codes is None:
                break
            previous_join_codes_sets.append([join_code.build_string() for join_code in join_codes])

        self.assertIsNone(join_codes)

        # Select instances to complete
        completed_join_code_set = random.choice(previous_join_codes_sets)
        for join_code_str in completed_join_code_set:
            task_manager.complete_join_code(join_code_str)

        join_codes = task_manager.get_next_join_codes()
        self.assertIsNotNone(join_codes)


if __name__ == '__main__':
    unittest.main()