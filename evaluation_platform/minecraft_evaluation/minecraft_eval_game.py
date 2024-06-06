import json
import os
import sys
from typing import Any, Dict

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from common import logger
from turn import Turn

_LOGGER = logger.get_logger(__name__)


class MinecraftEvalGame(Turn):
    """Class to represent a game that acts as buffer between the game storage and the mturk scripts.

    In minecraft evaluation, a HIT is created for multiple turns, therefore the
    class name is changed from Turn to Game.

    Contains all the data necessary to keep track of a game, and maps its attributes
    into the database schema.
    """

    def __init__(
            self, game_id: str, turn_type: str, task_name: str, agent_name: str,
            agent_id: str, join_code: str, **kwargs) -> None:
        super().__init__(game_id, turn_type, None)
        self.task_name: str = task_name
        self.agent_name: str = agent_name
        self.join_code: str = join_code
        self.agent_id: str = agent_id

        self.task_minecraft_id: str = None
        self.game_minecraft_id: str = None
        self.agent_minecraft_id: str = None
        self.completion_code: str = None
        # Annotator input for game
        self.annotation: Dict = {}
        # Path of game data inside results container
        self.result_game_data_path: str = None

    @classmethod
    def from_database_entry(cls, row: Dict[str, Any]):
        new_turn = cls(
            game_id=row['RowKey'],
            turn_type=row['HitType'],
            task_name=row['PartitionKey'],
            agent_name=row['AgentName'],
            join_code=row['JoinCode'],
            agent_id=row.get('AgentMinecraftId', 'NA')
        )
        new_turn.set_hit_id(row['HitId'])
        new_turn.is_qualified = row.get('IsHITQualified', 'NA')
        new_turn.worker_id = row.get('WorkerId', 'NA')
        new_turn.task_minecraft_id = row.get('TaskMinecraftId', 'NA')
        new_turn.game_minecraft_id = row.get('GameMinecraftId', 'NA')
        new_turn.result_blob_path = row.get('ResultGameDataPath', 'NA')
        new_turn.completion_code = row.get('CompletionCode', 'NA')
        new_turn.annotation = row.get('Annotation', {})
        return new_turn

    def to_database_entry(self) -> Dict[str, Any]:
        if self.hit_id is None:
            _LOGGER.warning(f'Attempting to save turn without created hit for game {self.game_id}')
            return None

        return {
            'PartitionKey': self.task_name,
            'RowKey': self.game_id,
            'AgentName': self.agent_name,
            'JoinCode': self.join_code,
            'HitId': self.hit_id,
            'HitType': self.turn_type,
            'AgentMinecraftId': self.agent_id or 'NA',
            'IsHITQualified': 'NA' if self.is_qualified is None else self.is_qualified,
            'WorkerId': self.worker_id or 'NA',
            'TaskMinecraftId': self.task_minecraft_id or 'NA',
            'GameMinecraftId': self.game_minecraft_id or 'NA',
            'ResultGameDataPath': self.result_game_data_path or 'NA',
            'CompletionCode': self.completion_code or 'NA',
            'Annotation': json.dumps(self.annotation),
        }
