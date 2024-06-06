"""
"""

import argparse
import binascii
from typing import Any, Dict, Optional, Tuple
import dotenv
import os
import sys

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))


from common import logger, utils
from minecraft_evaluation.data_collector import DataCollector, get_next_game_id
from minecraft_evaluation.minecraft_eval_game import MinecraftEvalGame
from minecraft_evaluation.minecraft_eval_template_renderer import AgentPairTemplateRenderer
from minecraft_evaluation.process_assignments import get_answer_from_assignment, validate_game_data
from minecraft_evaluation.game_events_handler import (
    MalformedConfirmationCodeException, BlobDataDownloadException)

dotenv.load_dotenv()

_LOGGER = logger.get_logger(__name__)
logger.set_logger_level('azure')


def read_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
       '--config',
       help='Environment to use for operations.',
       choices=['production', 'sandbox'],
       default='sandbox',
    )

    parser.add_argument(
       "--tasks_filepath",
       help="Path to json file with task names and join codes.",
       type=str, required=True,
    )

    parser.add_argument(
       '--agents_filepath',
       help="Path to json file with the map from agent name to agent instances.",
       type=str, required=True,
    )

    parser.add_argument(
       '--max_hits', help="Maximum number of hits to create.",
       type=int, default=5,
    )

    parser.add_argument(
       "--template_filepath",
       help="Path to the file with the html or xml or html template to render for each HIT.",
       type=str, default='templates/minecraft-eval-pairwise-agent.html',
    )

    return parser.parse_args()


def is_code_in_storage(game_storage, code) -> bool:
    entities = game_storage.retrieve_turn_entity(key=code, column_name= 'CompletionCode', n=1)
    return len(entities) > 0


def verify_pairwise_agent_assignment(
        assignment_dict, events_handler, game_storage) -> Tuple[bool, str]:
    """Asserts whether a pairwise agent assignment should be approved or not.

    For that, it fills assignment_dict with keys for the HIT values and
    downloads the game events.

    Approving criteria is:
        * Player as played at least three turns in each game
        * All players utterance are English
        * The completion code has not been used previously

    Args:
        assignment_dict (dictionary): A dictionary representation of the
            assignment, with at least keys 'InputInstruction'.

    Returns:
        Tuple[bool, str]: The bool indicates whether the assignment should be approved.
            The string is the error message that will be shown to the worker in case the
            assignment is rejected.
    """
    answer = get_answer_from_assignment(assignment_dict)
    if answer is None:
        return False

    # Add required keys to dict.
    assignment_dict['parsed_answers'] = answer
    assignment_dict['game_data1'] = None
    assignment_dict['game_data2'] = None

    # Keys in answer depend on the input elements in the HIT layout:
    completionCode1 = answer['completionCode1']
    completionCode2 = answer['completionCode2']

    if (completionCode1 == completionCode2 or
            is_code_in_storage(game_storage, completionCode1) or
            is_code_in_storage(game_storage, completionCode2)):
        return (False, 'You have used the same completion code more than once.')

    try:
        game_data1 = events_handler.get_game_data_for_completion_code(completionCode1)
        game_data2 = events_handler.get_game_data_for_completion_code(completionCode2)
    except (binascii.Error, MalformedConfirmationCodeException) as e:
        _LOGGER.error(
            f'Cannot retrieve game data for hit {assignment_dict["HitId"]}, '
            f'assignment {assignment_dict["AssignmentId"]}. '
            f'Malformed completion code \t {completionCode1} or \t {completionCode2}')
        return (
            False,
            'The completion code provided was invalid, but was built to circumvent the checks '
            'applied before submitting the HIT.'
        )
    except BlobDataDownloadException:
        _LOGGER.error(
            f'Cannot retrieve game data for hit {assignment_dict["HitId"]}, '
            f'assignment {assignment_dict["AssignmentId"]}. Missing data.'
        )
        return (
            'partial',
            'The completion code was well formed but we could not access your game data.')
    except Exception as e:
        _LOGGER.error(
            f'Cannot retrieve game data for hit {assignment_dict["HitId"]}, '
            f'assignment {assignment_dict["AssignmentId"]}. Unknown exception {e}'
        )
        return ('partial', '')

    assignment_dict['game_data1'] = game_data1
    assignment_dict['game_data2'] = game_data2

    qualified_game1, error_message1 = validate_game_data(game_data1, events_handler)
    qualified_game2, error_message2 = validate_game_data(game_data2, events_handler)

    error_message = ''
    if error_message1:
        error_message += 'Errors detected with first game: ' + error_message1
    if error_message2:
        error_message += 'Errors detected with second game: ' + error_message2
    qualified = True if qualified_game1 and qualified_game2 else 'partial'

    # TODO check completion code corresponds with join code.
    return qualified, error_message


class PairwiseDataCollector(DataCollector):

    turn_type = 'minecraft-eval-pairwise-agent'
    agent_combination_size = 2

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
        parsed_answers = assignment_answers['parsed_answers']
        if hit_game.join_code == parsed_answers['joinCode1']:
            annotation = {
                'was_chosen_best': parsed_answers['best_agent']['agent1_option'],
                'agent_performance': parsed_answers['agent1_performance']
            }
            hit_game.completion_code = parsed_answers['completionCode1']
            if assignment_answers['game_data1'] is not None:
                game_completion_data1 = assignment_answers['game_data1']['completionCodeData']
                hit_game.task_minecraft_id = game_completion_data1['task_id']
                hit_game.game_minecraft_id = game_completion_data1['game_id']

        elif hit_game.join_code == parsed_answers['joinCode2']:
            annotation = {
                'was_chosen_best': parsed_answers['best_agent']['agent2_option'],
                'agent_performance': parsed_answers['agent2_performance']
            }
            hit_game.completion_code = parsed_answers['completionCode2']
            if assignment_answers['game_data2'] is not None:
                game_completion_data2 = assignment_answers['game_data2']['completionCodeData']
                hit_game.task_minecraft_id = game_completion_data2['task_id']
                hit_game.game_minecraft_id = game_completion_data2['game_id']
        else:
            _LOGGER.warning(f"Join code {hit_game.join_code} not found in hit {hit_game.hit_id} result.")
            return None

        hit_game.worker_id = assignment_answers['WorkerId']
        hit_game.is_qualified = assignment_answers['IsHITQualified']
        hit_game.annotation = annotation
        return hit_game

    def create_hit(self) -> Optional[Tuple[MinecraftEvalGame, MinecraftEvalGame]]:
        """Selects a new set of available join codes and create a hit.

        Returns:
            Optional[str]: The new pair of games. Each game is already associated with
                the new HIT.
                If there are no available join codes, returns None.
        """
        join_codes = self.task_manager.get_next_join_codes()
        if join_codes is None:
            return None

        # Task name will be the partition key for the storage tables, and cannot
        # contain certain chars.
        join_code1 = join_codes[0]
        iglu_game_id = get_next_game_id()
        game1 = MinecraftEvalGame(
            game_id=iglu_game_id, turn_type=self.turn_type,
            task_name=join_code1.task_name.replace('/', '-'), agent_name=join_code1.agent_name,
            agent_id=join_code1.agent_instance_id, join_code=join_code1.build_string())

        join_code2 = join_codes[1]
        iglu_game_id = get_next_game_id()
        game2 = MinecraftEvalGame(
            game_id=iglu_game_id, turn_type=self.turn_type,
            task_name=join_code2.task_name.replace('/', '-'), agent_name=join_code2.agent_name,
            agent_id=join_code2.agent_instance_id, join_code=join_code2.build_string())

        # Create HIT for join codes
        template = self.renderer.render_template(
            game1.join_code, game2.join_code)
        new_hit_id = self.hit_manager.create_hit(
            template, hit_type=self.turn_type, **(self.config['hit_config']))

        game1.set_hit_id(new_hit_id)
        game2.set_hit_id(new_hit_id)
        _LOGGER.info(
            f"Hit created for games pair {join_code1.task_name}, "
            f"{join_code1.agent_name}, {join_code2.agent_name}")

        return (game1, game2)


def main():

    args = read_args()
    config = utils.read_config(args.config, config_filepath='./env_configs.json')

    config['azure_connection_str'] = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    config['azure_sas'] = os.getenv('AZURE_STORAGE_SAS')
    config['aws_access_key'] = os.getenv("AWS_ACCESS_KEY_ID_LIT")
    config['aws_secret_key'] = os.getenv("AWS_SECRET_ACCESS_KEY_LIT")
    config['minecraft_gamedata_container_url'] = os.getenv('MINECRAFT_GAMEDATA_CONTAINER_URL')
    config['minecraft_taskdata_container_url'] = os.getenv('MINECRAFT_TASKDATA_CONTAINER_URL')

    template_renderer = AgentPairTemplateRenderer(args.template_filepath)

    data_collector = PairwiseDataCollector(
        args.tasks_filepath, args.agents_filepath, template_renderer=template_renderer,
        verification_function=verify_pairwise_agent_assignment, config=config
    )

    data_collector.run_hits(max_completed_hits=args.max_hits, seconds_to_wait=30)


if __name__ == '__main__':
    main()
