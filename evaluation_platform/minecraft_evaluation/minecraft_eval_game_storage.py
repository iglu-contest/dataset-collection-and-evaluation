import os
import sys
from typing import Any, Dict, List, Optional
from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableServiceClient, TableClient, UpdateMode
from azure.storage.blob import ContainerClient
from random_word import RandomWords

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))


from game_storage import AzureGameStorage
from minecraft_eval_game import MinecraftEvalGame
from common import logger

_LOGGER = logger.get_logger(__name__)
logger.set_logger_level('azure')


class MinecraftEvalStorage(AzureGameStorage):
    """Abstraction of data structures to save game data in Azure tables and containers.

    This class is a context manager, use inside a with statement.
    >>> with AzureGameStorage(hits_table_name, azure_connection_string) as game_storage:
    ...     create_new_games(self, starting_structure_ids)

    Data is saved in two parts:
    * An Azure table contain HIT data.
    * An Azure container saves the generated game data in form of lists of events.
    """

    def __init__(self, hits_table_name: str, azure_connection_str: str,
                 result_game_data_blob_prefix: str,
                 result_game_data_container_name: str,
                 **kwargs) -> None:

        self.azure_connection_str = azure_connection_str
        self.result_game_data_blob_prefix = result_game_data_blob_prefix
        self.result_game_data_container_name = result_game_data_container_name
        self.hits_table_name = hits_table_name

        self.table_client = None

        self.container_client = None
        self.blob_service_client = None

    def retrieve_turn_entity(
            self, key: str, column_name: str = 'HitId', n : int = 1) -> List[Dict[str, Any]]:
        query_filter = f"{column_name} eq '{key}'"
        try:
            entities = self.table_client.query_entities(
                query_filter=query_filter,
                results_per_page=n)
            return [e for e in entities]

        except (ResourceExistsError, StopIteration):
            _LOGGER.warning(f'No turn with {column_name} = {key} found on table')
        return []

    def save_new_turn(self, game: MinecraftEvalGame):
        if game.hit_id is None:
            _LOGGER.warning(f"Attempting to save game without created hit for game {game.game_id}")
            return

        entity = game.to_database_entry()

        try:
            self.table_client.create_entity(entity)
            _LOGGER.debug(f'Successfully inserted new turn {game.hit_id} for game {game.game_id}.')
        except ResourceExistsError:
            _LOGGER.error(f"Game entry {game.hit_id} for game {game.game_id} already exists")

    def upsert_turn(self, game: MinecraftEvalGame):
        if game.hit_id is None:
            _LOGGER.warning(
                f"Attempting to upsert game without created hit for game {game.game_id}")
            return
        entity = game.to_database_entry()
        self.table_client.upsert_entity(mode=UpdateMode.MERGE, entity=entity)