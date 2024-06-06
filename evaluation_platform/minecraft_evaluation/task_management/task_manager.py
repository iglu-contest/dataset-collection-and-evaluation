import itertools
import json
import os
import random
import sys

from dataclasses import dataclass, asdict
from typing import List, Optional

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from common import priority_queue, logger

_LOGGER = logger.get_logger(__name__)


@dataclass
class JoinCode:
    task_name: str
    task_id: str
    task_join_code: str
    agent_name: str
    agent_instance_id: str

    def build_string(self):
        return f'{self.task_join_code}:{self.agent_instance_id}'

    def to_dict(self):
        return asdict(self)

    @classmethod
    def get_agent_instance_id_from_str(cls, join_code_str: str):
        return join_code_str.split(':')[-1]


class TaskManager:

    def __init__(
            self, task_info_filepath: str, agent_info_filepath: str,
            agent_combination_size: int) -> None:
        self.agent_combination_size = agent_combination_size
        # Map from task name to dictionary with keys "task_id" and "task_json_code".
        self.tasks = self.read_json_file(task_info_filepath)
        # Map from agent name to dictionary with keys "agent_instance_name" and "agent_instance_id".
        self.agents = self.read_json_file(agent_info_filepath)
        # Map from agent name to list of free instances ids
        self.free_agent_instances = {}
        for agent_name, agent_instances in self.agents.items():
            self.free_agent_instances[agent_name] = [
                agent_instance_info['agent_instance_id'] for agent_instance_info in agent_instances
            ]
        _LOGGER.info(f'Total {len(self.tasks)} tasks and instances {self._get_free_instances_for_log()}.')

        # Priority queue for the agent combinations where the priority is the number of times the
        # combination has been *selected*. I.e. when the it is *selected*, it lowers its priority.
        self.agent_combinations_queue = priority_queue.PriorityQueue()
        # Priority queues for each agent combination
        self.tasks_queues = {}
        for agent_combination in itertools.combinations(self.agents.keys(), agent_combination_size):
            self.agent_combinations_queue.enqueue(agent_combination, priority=0)
            self.tasks_queues[agent_combination] = priority_queue.PriorityQueue()
            # Shuffle task order for each agent combination
            task_names = [x for x in self.tasks.keys()]
            random.shuffle(task_names)
            for task_name in task_names:
                self.tasks_queues[agent_combination].enqueue(task_name, priority=0)

        self.generated_join_codes = set()

    @staticmethod
    def read_json_file(json_filepath):
        """Reads file from `json_filepath`."""
        with open(json_filepath, 'r') as json_file:
            return json.load(json_file)

    def is_agent_available(self, agent_name):
        return len(self.free_agent_instances[agent_name]) > 0

    def get_available_agents(self):
        return set([
            agent_name for agent_name, agent_instances in self.free_agent_instances.items()
            if len(agent_instances) > 0
        ])

    def _get_free_instances_for_log(self) -> str:
        return ' - '.join([f'{agent_name} : {len(free_instances)}'
                           for agent_name, free_instances in self.free_agent_instances.items()])

    def get_next_join_codes(self) -> Optional[List[JoinCode]]:
        """Gets codes for the highest priority agent_combination and task with free agent instances.

        This method uses both the task and agents priority queues.

        Returns:
            The list of join codes. It does not repeat any agent. If there are not enough agents
            with free instances, returns None
        """
        free_agents = self.get_available_agents()
        if len(free_agents) < self.agent_combination_size:
            _LOGGER.info(
                'No join codes can be created. Current available instances: ' + \
                self._get_free_instances_for_log()
            )
            return None

        # Step 1: select the highest priority agent combination with free instances.
        selected_agent_combination = None
        agents_to_requeue = []
        while selected_agent_combination is None and self.agent_combinations_queue.size > 0:
            current_priority = self.agent_combinations_queue.highest_priority
            candidate_agent_combination = self.agent_combinations_queue.dequeue()
            if candidate_agent_combination is None:
                break
            # All agents must be added back to the queue
            if not set(candidate_agent_combination).issubset(free_agents):
                agents_to_requeue.append((candidate_agent_combination, current_priority))
                continue
            agents_to_requeue.append((candidate_agent_combination, current_priority + 1))
            selected_agent_combination = candidate_agent_combination

        # Requeue discarded agent combinations
        for agent_combination, priority in agents_to_requeue:
            self.agent_combinations_queue.enqueue(agent_combination, priority)

        if selected_agent_combination is None:
            _LOGGER.info(
                'No join codes can be created. Current available instances: ' + \
               self._get_free_instances_for_log()
            )
            return None

        # Step 2: Select highest priority task and requeue with lower priority
        current_priority = self.tasks_queues[selected_agent_combination].highest_priority
        selected_task_name = self.tasks_queues[selected_agent_combination].dequeue()
        self.tasks_queues[selected_agent_combination].enqueue(selected_task_name)

        # Step 3: Build join codes and mark instances as used
        join_codes = []
        for agent_name in selected_agent_combination:
            join_code = self._get_join_code(selected_task_name, agent_name)
            join_codes.append(join_code)
            self.mark_instance_as_used(
                agent_name, join_code.agent_instance_id, join_code.build_string())

        return join_codes

    def mark_join_code_str_as_used(self, join_code_str: str, fail_ok=False):
        agent_instance_id = JoinCode.get_agent_instance_id_from_str(join_code_str)
        agent_name = None
        for candidate_agent_name, agent_instances in self.agents.items():
            for agent_instance_info in agent_instances:
                if agent_instance_info['agent_instance_id'] == agent_instance_id:
                    agent_name = candidate_agent_name
                    break
            if not agent_name is None:
                break
        if agent_name is not None:
            self.mark_instance_as_used(
                agent_name, agent_instance_id, join_code_str, fail_ok=fail_ok)

    def mark_instance_as_used(self, agent_name, agent_instance_id, join_code_str, fail_ok=False):
        """Removes instance from free_agent_instances."""
        if agent_instance_id in self.free_agent_instances[agent_name]:
            self.free_agent_instances[agent_name].remove(agent_instance_id)
        elif not fail_ok:
            _LOGGER.error(f'Attempt to mark instance {agent_instance_id} for agent '
                          f'{agent_name} as used, but instance was not free.')
        if join_code_str not in self.generated_join_codes:
            # This code is from a previous session
            self.generated_join_codes.add(join_code_str)

    def _get_join_code(self, task_name: str, agent_name: str) -> Optional[JoinCode]:
        """For a task and set of agents, returns codes for any free instance of each agent.

        If all instances for agent_name are currently busy, returns None.
        """
        task_info = self.tasks[task_name]

        selected_instance_id = self._get_free_instance(agent_name)
        if selected_instance_id is None:
            return None

        return JoinCode(
            task_name=task_name, agent_name=agent_name,
            task_id=task_info['task_id'],
            task_join_code=task_info['task_join_code'],
            agent_instance_id=selected_instance_id,
        )

    def _get_free_instance(self, agent_name: str) -> Optional[str]:
        if len(self.free_agent_instances[agent_name]) == 0:
            return None
        return self.free_agent_instances[agent_name][0]

    def is_instance_in_use(self, agent_name: str, agent_instance_id: str) -> bool:
        return agent_instance_id not in self.free_agent_instances[agent_name]

    def complete_join_code(self, join_code_str: str):
        """Mark the agent_instance associated to the join_code as free."""
        if join_code_str not in self.generated_join_codes:
            # This code is from a previous session, so the instance should not be freed.
            return

        agent_instance_id = JoinCode.get_agent_instance_id_from_str(join_code_str)
        agent_name = None
        for candidate_agent_name, agent_instances in self.agents.items():
            for agent_instance_info in agent_instances:
                if agent_instance_info['agent_instance_id'] == agent_instance_id:
                    agent_name = candidate_agent_name
                    break
            if not agent_name is None:
                break
        if agent_name is None:
            _LOGGER.error(f"Cannot find agent for agent instance is join code {join_code_str}")
            return

        if agent_instance_id in self.free_agent_instances[agent_name]:
            _LOGGER.error(
                'Attempt to complete join code for a free instance. '
                f'Agent: {agent_name} - agent_instance_id: {agent_instance_id}')
        else:
            # Mark agent instance as free
            self.free_agent_instances[agent_name].append(agent_instance_id)
