import datetime
import os
import sys
import time
import uuid

from functools import partial
from typing import Any, Callable, Dict, List, Optional, Tuple
from random_word import RandomWords

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from common import logger
from minecraft_evaluation.game_events_handler import GameEventsHandler
from minecraft_evaluation.minecraft_eval_game import MinecraftEvalGame
from minecraft_evaluation.minecraft_eval_game_storage import MinecraftEvalStorage
from minecraft_evaluation.minecraft_eval_hit_manager import MinecraftEvalHitManager
from minecraft_evaluation.minecraft_eval_template_renderer import TemplateRenderer
from minecraft_evaluation.task_management.task_manager import TaskManager

_LOGGER = logger.get_logger(__name__)


def get_next_game_id():
    """Example of generating a fast new random game id."""
    word_generator = RandomWords()
    return word_generator.get_random_word() + '-' + str(uuid.uuid4())


class DataCollector:

    turn_type = 'minecraft-eval'
    agent_combination_size = 1
    # Worker ids used for testing. Do not block even if they have too many rejected hits.
    never_block_worker_ids = [
        'A1IM8WAQ7QR34E'
    ]

    def __init__(
            self, tasks_filepath: str, agents_filepath: str, template_renderer: TemplateRenderer,
            verification_function: Callable, config: Dict[Any, Any]):
        """Creates new DataCollector

        Args:
            tasks_filepath (str): Path to json file with task names and join codes.
            agents_filepath (str): Path to json file with the map from agent name to
                agent instances.
            template_renderer (TemplateRenderer): The renderer instance used to create the hits
            verification_function (Callable): _description_
            config (dict): General experiment configuration, containing at least keys
                * 'minecraft_taskdata_container_url'
                * 'minecraft_gamedata_container_url'
                * 'hit_config' with parameters for method `MinecraftEvalHitManager.create_hit`
                * arguments of classes `MinecraftEvalHitManager` and `MinecraftEvalStorage`
        """
        self.task_manager = TaskManager(
            tasks_filepath, agents_filepath, agent_combination_size=self.agent_combination_size)
        self.completed_hits_count = 0

        self.renderer = template_renderer
        self.game_events_handler = GameEventsHandler(
            config['minecraft_taskdata_container_url'],
            config['minecraft_gamedata_container_url']
        )
        self.verification_function = verification_function
        self.config = config

    def wait_for_assignments(self, game_storage, max_completed_hits, seconds_to_wait=60):
        """Loop that retrieves new completed assignments from mturk.

        Processes assignments them until max_completed_hits is reached.

        Args:
            game_storage (_type_): _description_
            max_completed_hits (int): _description_.
            seconds_to_wait (int, optional): _description_. Defaults to 60.
        """
        while self.completed_hits_count < max_completed_hits:
            # Look for further open hits
            open_hit_ids = self.hit_manager.get_open_hit_ids_by_status(
                hit_type=self.turn_type, remove_expired=True)

            # There are no open hits
            if sum([len(hit_ids) for hit_status, hit_ids in open_hit_ids.items()]) == 0:
                self.create_all_hits_possible(
                    max_completed_hits - self.completed_hits_count, game_storage)
                continue

            # Look for new submitted assignments and review them. This returns a map from
            # hit_id to another dict with assignment information.
            completed_assignments = self.hit_manager.complete_open_assignments(
                open_hit_ids.get('open', []) + open_hit_ids.get('to_close', []))
            completed_hits = set([hit_id for hit_id in completed_assignments.keys()])

            # Free instances of hits that have expired but do not have any assignment
            for hit_id in open_hit_ids.get('to_close', []) + open_hit_ids.get('deleted', []):
                if hit_id in completed_hits:
                    continue
                game_entities = game_storage.retrieve_turn_entity(hit_id, 'HitId')
                if game_entities is None or len(game_entities) == 0:
                    _LOGGER.error(f'No turn found in database for HIT {hit_id}')
                    continue

                for game_entity in game_entities:
                    hit_game = MinecraftEvalGame.from_database_entry(game_entity)
                    # Mark used instances as free, regardless of assignment result
                    self.complete_game_join_code(hit_game)

            # If there were assignments completed in the previous function, save the
            # results into the game storage.
            if len(completed_assignments) == 0:
                _LOGGER.info(f"No new assignments, waiting for {seconds_to_wait} seconds.")
                time.sleep(seconds_to_wait)
                continue

            self.save_completed_hits(completed_assignments, game_storage)
            # Even if there is an error with the assignment, we still count it to avoid
            # infinite loops in case of a bug.
            self.completed_hits_count += len(completed_assignments)
            remaining_open_hits = len(open_hit_ids) - len(completed_assignments)

            # For each completed hit, if more are needed, attempt to re-create it.
            # self.create_all_hits_possible(
            #     max_completed_hits - remaining_open_hits - self.completed_hits_count,
            #     game_storage)

    def update_game_with_assignment(
            self, hit_game: MinecraftEvalGame,
            assignment_answers: Dict[str, Any]) -> Optional[MinecraftEvalGame]:
        """Update the turn associated to the assignment with the retrieved answer.

        Args:
            hit_game (MinecraftEvalGame): Game entity that corresponds to the
                assignment's hit. This entity will be updated
            assignment_answers (dict): a dictionary with the answers to the assignment.

        Returns:
            Optional[MinecraftEvalGame]: A reference to hit_game with the updated
            values taken from the assignment answer.
        """
        raise NotImplementedError

    def complete_game_join_code(self, hit_game: MinecraftEvalGame):
        """Notify task_manager the instances associated to the join codes are free.

        Args:
            hit_game (MinecraftEvalGame): the game associated with the join code.
                Ideally, the hit for the game should have been submitted before calling
                this method, to avoid creating another HIT with the same instance id.
        """
        self.task_manager.complete_join_code(hit_game.join_code)

    def save_completed_hits(
            self, completed_assignments: Dict[str, Any], game_storage: MinecraftEvalStorage):
        """Update the game entities in the storage with the result for all completed assignments.

        The method retrieves the entity associated to the HIT, created along with the HIT,
        and updates the answer

        Args:
            completed_assignments (Dict): Dictionary mapping the hit_id with a submitted
            assignment. Requires at least key 'parsed_answers' with the result of each assignment.
            game_storage (MinecraftEvalStorage): The GameStorage used to store the collected data.
        """
        for hit_id, assignment_answers in completed_assignments.items():
            # Retrieve the open games in this hit.
            game_entities = game_storage.retrieve_turn_entity(hit_id, 'HitId')
            if game_entities is None or len(game_entities) == 0:
                _LOGGER.error(f'No turn found in database for HIT {hit_id}')
                continue

            for game_entity in game_entities:
                hit_game = MinecraftEvalGame.from_database_entry(game_entity)

                # Mark used instances as free, regardless of assignment result
                self.complete_game_join_code(hit_game)

                hit_game = self.update_game_with_assignment(hit_game, assignment_answers)
                if not hit_game.is_qualified:
                    self.block_worker(assignment_answers['WorkerId'], game_storage)

                if hit_game is not None:
                    game_storage.upsert_turn(hit_game)
                # TODO copy downloaded game data into results storage

            _LOGGER.info(f"Assignment for hit {hit_id} saved.")

    def block_worker(self, worker_id, game_storage, max_disqualified_hits=2):
        """Block a worker from new HITs if they have too many rejected HITs."""
        if worker_id in self.never_block_worker_ids:
            return

        worker_hits = game_storage.retrieve_turn_entity(key=worker_id, column_name='WorkerId')
        disqualified_tasks = 0
        for row in worker_hits:
            if row.get('IsHITQualified', 'NA') == False:
                disqualified_tasks += 1
        if disqualified_tasks >= max_disqualified_hits * 2:  # 2 turns for every hit
            self.hit_manager.block_worker(worker_id, 'Too many disqualified tasks')

    def create_hit(self) -> Optional[Tuple[MinecraftEvalGame, MinecraftEvalGame]]:
        """Selects a new set of available join codes and create a hit.

        Returns:
            Optional[str]: The new games associated to the hit.
                If there are no available join codes, returns None.
        """
        raise NotImplementedError

    def save_new_games_to_storage(
            self, hit_games: List[MinecraftEvalGame], game_storage: MinecraftEvalStorage):
        """Stores the games associated to the hit to the game_storage.

        In the base case, a single game is created per HIT, but there could be more than one.
        """
        for hit_game in hit_games:
            game_storage.save_new_turn(hit_game)

    def create_all_hits_possible(self, max_hits, game_storage):
        hits_count = 0
        while hits_count < max_hits:
            hit_games = self.create_hit()
            if hit_games is None:
                return
            self.save_new_games_to_storage(hit_games, game_storage)
            hits_count += 1

    def run_hits(self, max_completed_hits, seconds_to_wait=60):
        """Continuously generates and approves HITs until the desired number is completed.

        Args:
            max_completed_hits (int, optional): Number of hits to complete before
                finishing script.
            seconds_to_wait (int, optional): Seconds to wait before querying mturk for new
                available assignments. Defaults to 60.
        """

        with MinecraftEvalStorage(**self.config) as game_storage:
            self.hit_manager = MinecraftEvalHitManager(
                verification_function=partial(
                    self.verification_function, events_handler=self.game_events_handler,
                    game_storage=game_storage),
                **self.config
            )
            # Collect previous HITs and mark instances as used
            # Hits returned have states
            initial_hits = self.hit_manager.get_open_hit_ids(hit_type=self.turn_type)
            for hit_id in initial_hits:
                game_entities = game_storage.retrieve_turn_entity(hit_id, 'HitId')
                for game in game_entities:
                    self.task_manager.mark_join_code_str_as_used(
                        join_code_str=game['JoinCode'], fail_ok=True)

            # Create new hits for each task to collect until no instances are available.
            self.create_all_hits_possible(max_completed_hits - len(initial_hits), game_storage)

            _LOGGER.info("Initial HITs created successfully, waiting for assignments submissions")
            self.wait_for_assignments(game_storage, max_completed_hits, seconds_to_wait)
