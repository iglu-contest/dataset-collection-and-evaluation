import argparse
import base64
import datetime
import os
import dotenv
import gzip
import json
import requests
import sys

from typing import Dict, List, Optional, TypedDict

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from common import logger


dotenv.load_dotenv()
_LOGGER = logger.get_logger(__name__)
logger.set_logger_level('azure')


class MalformedConfirmationCodeException(Exception):
    """
    Raised when we try to parse a confirmation code which is malformed.
    """


class BlobDataDownloadException(Exception):
    """
    Raised when we fail to download task data from the blob.
    """

class Location(TypedDict):
    x: int
    y: int
    z: int
    pitch: int
    yaw: int


class MovementRegion(TypedDict):
    origin: Location
    size: Location


class PlayerState(TypedDict):
    movementRegion: Optional[MovementRegion]
    spawnLocation: Location


class BlockInfo(TypedDict):
    type: int


class WorldState(TypedDict):
    blobkChanges: Dict[str, BlockInfo]
    generatorName: str


class InitialGameState(TypedDict):
    instructions: str
    playerStates: Dict[str, PlayerState]
    worldState: WorldState


class TargetGameChanges(TypedDict):
    worldChanges: WorldState


class BlobTaskData(TypedDict):
    initialGameState: InitialGameState
    targetGameChanges: List[TargetGameChanges]


class BaseEventData(TypedDict, total=False):
    eventType: str
    id: str
    gameId: str
    taskId: str
    tournamentId: str
    producedAtDatetime: datetime.datetime
    source: str
    roleId: Optional[str]
    groupId: Optional[str]
    agentSubscriptionFilterValue: Optional[str]


class BlobGameEvents(TypedDict):
    game_id: str
    events: List[BaseEventData]


class CompletionCodeData(TypedDict):
    tournament_id: str
    challenge_type: str
    challenge_id: str
    task_id: str
    game_id: str
    role_id: str
    agent_service_id: str


class GameResults(TypedDict):
    gameEvents: List[BaseEventData]
    taskData: BlobTaskData
    completionCodeData: CompletionCodeData


class GameEventsHandler:

    def __init__(self, task_data_container_url, game_data_container_url):
        self.task_data_container_url = task_data_container_url
        self.game_data_container_url = game_data_container_url

    def get_game_data_for_completion_code(self, completion_code: str) -> GameResults:
        """
        Given a confirmation code, it returns a GameResults instance with all the data for that game.

        Returns:
            (GameResults) a TypedDict with task, game event and completion code information

        Raises:
            MalformedConfirmationCodeException
            BlobDataDownloadException
        """
        completion_code_data, legacy_code = self._parse_completion_code(completion_code)

        task_data = self._download_task_data(completion_code_data["task_id"])
        game_data = self._download_game_data(completion_code_data, legacy_code)

        return GameResults(
            gameEvents=game_data["events"],
            taskData=task_data,
            completionCodeData=completion_code_data
        )

    @staticmethod
    def get_player_id(game_result: GameResults) -> str:
        """Returns the id of the player who generated the confirmation code for this game.

        Args:
            game_result (GameResults): the result of calling self.get_game_data_for_completion_code

        Returns:
            str: the player id.
        """
        return game_result['completionCodeData']['role_id']

    @staticmethod
    def filter_events_by_type(
            game_result: GameResults, event_types: List[str],
            from_player: str = None) -> List[BaseEventData]:
        filtered_events = []
        for game_event in game_result['gameEvents']:
            if (game_event['eventType'] in event_types and
                (from_player is not None or game_event['role_id'] == from_player)):
                filtered_events.append(game_event)
        return filtered_events

    @staticmethod
    def _parse_completion_code(completion_code: str) -> CompletionCodeData:
        """
        Parse the completion code into it's separate IDs.

        The completion code is expected to be GZipped and base64-encoded.

        Once decoded, the format of the completion code is as follows:

            {tournament_id}:{challenge_type}:{challenge_id}:{task_id}:{game_id}:{role_id}:{agent_service_id}

        Where all fields are GUIDs except for `challenge type` which is either `ac`
        or `hc`, depending on whether it's an `agent challenge` or `human
        challenge`.
        """
        _LOGGER.debug(f"Parsing completion code: {completion_code}")
        try:
            code_bytes = base64.b64decode(completion_code)
            completion_code = gzip.decompress(code_bytes).decode("utf-8")
        except:
            raise MalformedConfirmationCodeException(
                f"Completion code '{completion_code}' is malformed. "
                "Cannot be uncompressed.")

        components = completion_code.split(':')

        if components[2] == 'hc':
            # human challenge are not supported. The code in this script assumes
            # that the game we're working with is from an agent challenge
            raise NotImplementedError("Human challenge completion codes are not supported yet")

        is_legacy = False
        if len(components) == 7:
            (tournament_id,
            challenge_type,
            challenge_id,
            task_id,
            game_id,
            role_id,
            agent_service_id) = components
        elif len(components) == 8:
            (tournament_id,
            challenge_type,
            challenge_id,
            task_id,
            game_id,
            role_id,
            _,
            agent_service_id) = components
            is_legacy = True
            _LOGGER.warning("Reading legacy completion code! Unsupported fields will be ignored.")
        else:
            raise MalformedConfirmationCodeException(
                f"Completion code '{completion_code}' is malformed. "
                f"Expected 7 components, got {len(components)}")

        return CompletionCodeData(
            tournament_id=tournament_id,
            challenge_type=challenge_type,
            challenge_id=challenge_id,
            task_id=task_id,
            game_id=game_id,
            role_id=role_id,
            agent_service_id=agent_service_id
        ), is_legacy

    def _download_task_data(self, task_id: str) -> BlobTaskData:
        _LOGGER.debug(f"Downloading data for task: {task_id}")

        base_url = f'{self.task_data_container_url}/{task_id}'

        def _get_json(url: str) -> dict:
            _LOGGER.debug(f"Downloading data from: {url}")
            response = requests.get(url)
            if response.status_code != 200:
                raise BlobDataDownloadException(
                    f"Failed to download data from {url}. "
                    f"Status code: {response.status_code}")
            return response.json()

        task_data: BlobTaskData = {
            "initialGameState": InitialGameState(**_get_json(f'{base_url}/initialGameState.json')),
            "targetGameChanges": [TargetGameChanges(**t) for t in _get_json(f'{base_url}/targetGameChanges.json')],
        }

        return task_data

    def _download_game_data(self, completion_data: CompletionCodeData, legacy_code=False):
        """
        Download the game data from the blob storage.
        """

        _LOGGER.debug(f"Downloading game data for game id: {completion_data['game_id']}")

        if not legacy_code:
            group_id_components = [
                completion_data["tournament_id"],
                completion_data["challenge_type"],
                completion_data["challenge_id"],
            ]
        else:
            group_id_components = [
                completion_data["tournament_id"],
                completion_data["challenge_id"],
                completion_data["task_id"],
                completion_data["agent_service_id"],
            ]

        group_id = ':'.join(group_id_components)

        game_data_url = (
            f'{self.game_data_container_url}/tournaments/{completion_data["tournament_id"]}'
            f'/groupId/{group_id}'
            f'/tasks/{completion_data["task_id"]}'
            f'/games/{completion_data["game_id"]}.json'
        )

        data = requests.get(game_data_url)
        if data.status_code != 200:
            raise BlobDataDownloadException(f"Blob request status code {data.status_code}")
        data = data.json()

        return BlobGameEvents(game_id=data['id'], events=data['events'])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="download_game_data_from_completion_code",
        description=("Download game data associated with a completion code and prints it to "
                     "stdout as JSON object.")
    )

    parser.add_argument("--loglevel", default="INFO", help="Set the log level")
    parser.add_argument("completion_code", help="The completion code to download the game data for. Is is expected to be GZipped "
                        "and base64-encoded.")

    args = parser.parse_args()

    _LOGGER.setLevel(args.loglevel)
    completion_code = args.completion_code

    task_data_container_url = os.getenv('MINECRAFT_TASKDATA_CONTAINER_URL')
    game_data_container_url = os.getenv('MINECRAFT_GAMEDATA_CONTAINER_URL')
    game_data_downloader = GameEventsHandler(
        task_data_container_url, game_data_container_url)
    game_results = game_data_downloader.get_game_data_for_completion_code(completion_code)

    print(json.dumps(game_results, indent=4, sort_keys=True, default=str))
