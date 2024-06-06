import binascii
import json
import os
import sys
from typing import Tuple

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from common import logger, utils
from minecraft_evaluation.game_events_handler import (
    MalformedConfirmationCodeException, BlobDataDownloadException)

_LOGGER = logger.get_logger(__name__)


def get_answer_from_assignment(assignment_dict):
    answer_list = []
    if not type(assignment_dict['Answer']) is list:
        # One field found in HIT layout
        answer_list = [assignment_dict['Answer']]
    else:
        # Multiple fields in HIT layout
        answer_list = assignment_dict['Answer']

    json_answer = None
    for answer_field in answer_list:
        if answer_field['QuestionIdentifier'] == 'taskAnswers':
            json_answer = answer_field['FreeText']
            break

    if json_answer is None:
        return None
    try:
        answers = json.loads(json_answer)
    except (json.JSONDecodeError, ValueError):
        return None
    if len(answers) == 0:
        return None

    return answers[0]


def validate_game_data(game_data, events_handler, min_turns=3) -> Tuple[bool, str]:
    """Iterates over game data and returns whether the game is approved.

    Approving criteria is:
        * Player as played at least three turns
        * All players utterance are English

    Args:
        game_data (GameResults): The list of events returned by GameEventsHandler
        events_handler (GameEventsHandler): an instance of the event handler.

    Returns:
        bool: Returns true if the assignment passes the validation criteria
    """
    # Get the player id
    annotator_player_id = events_handler.get_player_id(game_data)

    # Obtain relevant events
    relevant_event_types = ['PlatformPlayerTurnChangeEvent', 'PlayerChatEvent']
    annotator_turn_changes = 0
    annotator_chat_messages = []
    filtered_events = events_handler.filter_events_by_type(
        game_data, relevant_event_types, from_player=annotator_player_id)
    for event in filtered_events:
        if (event['source'] != 'MinecraftPlugin'):
            continue
        if (event['eventType'] == 'PlatformPlayerTurnChangeEvent' and
                event['reason'] == 'PLAYER_COMMAND'):
            annotator_turn_changes += 1
        elif (event['eventType'] == 'PlayerChatEvent'):
            annotator_chat_messages.append(event['message'])

    # Apply checks
    qualified = True
    error_messages = []
    if annotator_turn_changes < min_turns:
        for message in annotator_chat_messages:
            if not (len(message.strip()) > 5 and utils.is_english(message)):
                qualified = False
                error_messages.append(f"The instruction {message} was not correct.")
    else:
        qualified = False
        error_messages.append(
            f"The game had not enough turns. The minimum number or turns is {min_turns}.")

    # TODO validate the completion code corresponds to the same task/agent as join code.
    return qualified, ' '.join(error_messages)
