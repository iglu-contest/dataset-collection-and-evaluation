"""Create HITs for a single turn of minecraft evaluation.

Continuously monitor and approve submitted assignments for created hits. Script
runs until there are no more open hits, i.e., hits that are not expired and that
are not already reviewed. It can be terminated prematurely with a kill signal,
in which case the new submitted assignments can be retrieved and approved if
the script is executed again, before the assignment expires.
"""

import argparse
import binascii
from typing import Any, Dict, List, Optional, Tuple
import dotenv
import os
import sys

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))


from common import logger, utils
from minecraft_evaluation.data_collector import DataCollector, get_next_game_id
from minecraft_evaluation.minecraft_eval_template_renderer import SingleAgentTemplateRenderer
from minecraft_evaluation.minecraft_eval_game import MinecraftEvalGame
from minecraft_evaluation.process_assignments import get_answer_from_assignment, validate_game_data

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
       '--agents_filepath', help="Path to json file with the map from agent name to agent instances.",
       type=str, required=True,
    )

    parser.add_argument(
       '--max_hits', help="Maximum number of hits to create.",
       type=int, default=5,
    )

    parser.add_argument(
       "--template_filepath",
       help="Path to the file with the xml or html template to render for each HIT.",
       type=str, default='templates/minecraft-eval-single-agent.html',
    )

    return parser.parse_args()


def verify_single_agent_assignment(assignment_dict, events_handler) -> Tuple[bool, str]:
    """Asserts whether a single agent assignment should be approved or not.

    Parses the assignment answers.
    It downloads the game events from the completion code present on the assignment
    responses. Fills assignment_dict with keys that contain the extracted assignment answers.


    Approving criteria is:
        * Player as played at least three turns
        * All players utterance are English

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
    assignment_dict['CompletionCode'] = answer['completionCode']
    assignment_dict['TextFeedback'] = answer['generalFeedback']
    assignment_dict['JoinCode'] = answer['joinCode']

    try:
        game_data = events_handler.get_game_data_for_completion_code(answer['completionCode'])
    except:
        _LOGGER.error(
            f'Cannot retrieve game data for hit {assignment_dict["HitId"]}, '
            f'assignment {assignment_dict["AssignmentId"]}. '
            f'Malformed completion code {answer["completionCode"]}')
        return False

    assignment_dict['game_data'] = game_data
    if game_data == None:
        # If the completion code can't be parsed, then we reject the hit.
        _LOGGER.error(
            f'Cannot retrieve game data for assignment {assignment_dict["AssignmentId"]}')
        return False

    qualified_game, error_message = validate_game_data(game_data, events_handler)
    # TODO notify user of infringement, but still approve assignment.
    # TODO check the completion code has not been used previously.
    return qualified_game, error_message


class SingleAgentDataCollector(DataCollector):

    turn_type = 'minecraft-eval-single-agent'
    agent_combination_size = 1

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
        hit_game.completion_code = assignment_answers['CompletionCode']
        hit_game.is_qualified = assignment_answers['IsHITQualified']
        hit_game.worker_id = assignment_answers['WorkerId']

        # Any other information can go in the `annotation` field, which will be saved as json.
        # hit_game.annotation = {}

        return hit_game

    def create_hit(self) -> Optional[List[MinecraftEvalGame]]:
        """Selects a new set of available join codes and create a hit.

        Returns:
            Optional[str]: A list where the only element is the new game associated
                with the HIT. If there are no available join codes, returns None.
        """
        join_codes = self.task_manager.get_next_join_codes()
        if join_codes is None:
            return None

        join_code = join_codes[0]
        iglu_game_id = get_next_game_id()
        # Task name will be the partition key for the storage tables, and cannot
        # contain certain chars.
        game = MinecraftEvalGame(
            game_id=iglu_game_id, turn_type=self.turn_type,
            task_name=join_code.task_name.replace('/', '-'), agent_name=join_code.agent_name,
            agent_id=join_code.agent_instance_id, join_code=join_code.build_string())

        # Create HIT for join code
        template = self.renderer.render_template(
            join_code.build_string(), join_code.task_name, join_code.agent_name)
        new_hit_id = self.hit_manager.create_hit(
            template, hit_type=self.turn_type, **(self.config['hit_config']))

        game.set_hit_id(new_hit_id)

        return (game, )


def main():

    args = read_args()
    config = utils.read_config(args.config, config_filepath='./env_configs.json')

    config['azure_connection_str'] = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    config['azure_sas'] = os.getenv('AZURE_STORAGE_SAS')
    config['aws_access_key'] = os.getenv("AWS_ACCESS_KEY_ID_LIT")
    config['aws_secret_key'] = os.getenv("AWS_SECRET_ACCESS_KEY_LIT")
    config['minecraft_gamedata_container_url'] = os.getenv('MINECRAFT_GAMEDATA_CONTAINER_URL')
    config['minecraft_taskdata_container_url'] = os.getenv('MINECRAFT_TASKDATA_CONTAINER_URL')

    template_renderer = SingleAgentTemplateRenderer(args.template_filepath)

    data_collector = SingleAgentDataCollector(
        args.tasks_filepath, args.agents_filepath, template_renderer=template_renderer,
        verification_function=verify_single_agent_assignment, config=config
    )

    data_collector.run_hits(max_completed_hits=args.max_hits, seconds_to_wait=30)


if __name__ == '__main__':
    main()
