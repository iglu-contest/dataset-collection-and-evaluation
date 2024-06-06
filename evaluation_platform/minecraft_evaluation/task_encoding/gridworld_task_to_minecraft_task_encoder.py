import json
import jinja2
import os
from itertools import product
from typing import Dict, List, Literal, Tuple, Optional

import iglu_task_default_values

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


# (X, Y, Z, Block ID)
BlockLocation = Tuple[int, int, int, int]


class GridworldTaskToMinecraftTaskEncoder:
    """
    Encoder to convert gridworld tasks to json files accepted by the Minecraft Data Collection Tool.
    """

    def __init__(
            self,
            architect_role_id: str,
            builder_role_id: str,
            task_template_filepath: str):
        """Create new encoder for specific player roles based on the given template.

        Args:
            architect_role_id (str): The role id of the architect. It should be obtained from
                the minecraft data collection platform.
            builder_role_id (str): The role id of the builder. It should be obtained from
                the minecraft data collection platform.
            task_template_filepath (str): Path to the jinja template that will
                be filled every time the `convert` method is called.
        """
        self.architect_role_id = architect_role_id
        self.builder_role_id = builder_role_id

        template_dirpath = os.path.dirname(task_template_filepath)
        template_filename = os.path.basename(task_template_filepath)
        jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(
            template_dirpath
        ))

        self.jinja_template = jinja_environment.get_template(template_filename)

    def convert(
        self,
        task_name: str,
        task: tasks.Task,
        task_state: Literal["Published", "Draft"] = "Published",
        world_size_x: int = 160,
        world_size_z: int = 160,
        game_limit_max_duration_seconds: int = 60*60,
        game_limit_max_turns: Optional[int] = None,
        turn_limits: Optional[Dict[str, int]] = None,
    ) -> str:
        """Encode gridworld tasks to a json file using the encoder template.

        Args:
            task_name (str): The name of the task that will be displayed on Dashboard.
            task (tasks.Task): the gridworld task to convert
            task_state (Literal[&quot;Published&quot;, &quot;Draft&quot;]): The current state of
                the task. Unused
            world_size_x (int, optional): Size of the world along with x dimension, in blocks,
                passed to the Agent as a representation of the world state. Unused. Defaults to 160.
            world_size_z (int, optional): Size of the world along with z dimension, in blocks,
                passed to the Agent as a representation of the world state. Defaults to 160.
            game_limit_max_duration_seconds (int, optional): Maximum time for all games associated to
                this task. Games will be automatically ended after this time in seconds has passed.
                Defaults to 60*60.
            game_limit_max_turns (int | None, optional): Maximum number of turns for all games
                associated to this task. Games will be automatically ended after this number of
                turns has passed. Defaults to None, in which case the game will play indefinitely.
            turn_limits (Dict[str, int] | None, optional): Maximum number of turns for each role
                for all games associated to this task. The keys of the dictionary are the
                role ids, and the values are the number of turns. Games will be automatically
                ended after this number of turns has passed. Defaults to None, in which case the
                game will play indefinitely.

        Returns:
            (str): The json string representing the task.
        """

        # Special chars like newlines are encoded for json. Prefer this method because
        # Jinja filter encoding will also escape < and > symbols.
        player_states = {
            self.architect_role_id: iglu_task_default_values.ARCHITECT_ATTRIBUTES,
            self.builder_role_id: iglu_task_default_values.BUILDER_ATTRIBUTES
        }

        game_limits = {
            "maxDurationSeconds": game_limit_max_duration_seconds
        }

        if game_limit_max_turns is not None:
            game_limits["maxTurns"] = game_limit_max_turns

        # remove last_instruction from chat if present
        chat = task.chat
        chat_utterances = chat.split("\n")
        if len(chat_utterances) > 0 and chat_utterances[-1] == task.last_instruction:
            chat = "\n".join(chat_utterances[:-1])

        instructions = json.dumps(chat)
        rendered_task = self.jinja_template.render(
            task_name=task_name,
            task_instructions=instructions,
            initial_world_block_changes=self._get_initial_world_block_changes(task),
            player_states=player_states,
            target_game_states=self._get_target_block_changes(task),
            task_state=task_state,
            world_size_x=world_size_x,
            world_size_z=world_size_z,
            game_limits=game_limits,
            turn_limits=turn_limits,
        )
        return rendered_task

    def _get_initial_world_block_changes(self, task: tasks.Task) -> Dict:
        block_changes = iglu_task_default_values.FLOOR_BLOCK_CHANGES.copy()
        block_changes.update(iglu_task_default_values.CARDINAL_LETTERS_BLOCK_CHANGES)

        # append new blocks from task to initial world state
        for initial_block in task.starting_grid:
            coords, tpe = self._convert_gridworld_block_location_to_plugin(initial_block)
            block_changes[coords] = tpe

        return block_changes

    @staticmethod
    def _get_corrected_target_grid(task: tasks.Task) -> Dict:
        """Returns a sparse representation of the target_grid with coordinates shifted to match
        Minecraft world origin.

        The sparse representation only contains blocks that are not air.

        Coordinate dimensions are normalized to order XYZ, correcting y so lowest is -1, not 0.
        x and z in the original target grid are shifted +5 so that the "space"
        of the target structure is with 0, 0 at the top left. The structure should be centered,
        so the coordinates are shifted -5 places. The new target structure has range (-5, 5) in
        both x and z axis.

        Returns:
            Dict:
        """
        sparse_target_grid = []
        for (y, x, z) in product(*map(range, task.target_grid.shape)):
            block_id = task.target_grid[y, x, z]
            if block_id != 0:
                sparse_target_grid.append((x-5, y-1, z-5, block_id))

        return sparse_target_grid

    def _get_target_block_changes(self, task: tasks.Task) -> List:
        # The template key `targetGameChanges` should contain a list of `GameChanges`.
        # For Gridworld task, there is only one target game composed of block changes.
        corrected_target_grid = self._get_corrected_target_grid(task)

        target_game_changes = {
            "worldChanges": {"blockChanges": {}}
        }

        for target_block in corrected_target_grid:
            coords, tpe = self._convert_gridworld_block_location_to_plugin(target_block)
            target_game_changes["worldChanges"]["blockChanges"][coords] = tpe

        return [target_game_changes]

    @staticmethod
    def _convert_gridworld_block_location_to_plugin(
            block_location: BlockLocation) -> Tuple[str, Dict]:
        """
        Takes a tuple that tells us the location and material of a block in gridworld and
        returns a new pair of locations encoded as strings and a dict with the block type:

        For example, (-10,-1,-3,1) would get converted to

            "[-10.0,1.0,-3.0,0.0,0.0]"  { "type": 174 }

        Note that this method will both convert the internal gridworld block ID to a valid
        minecraft block Id, as well as correct the positions.

        List of minecraft block IDs was obtained with the following code:

        ```
        for (var entry : BlockUtils.MATERIAL_IDS.entrySet()) {
            if (entry.getKey().name().contains("WOOL")) {
                MinecraftLogger.info(">> %s: %s".formatted(entry.getKey(), entry.getValue()));
            }
        }
        ```
        """
        x, y, z, block_id = block_location
        y += 2  # lowest block can be -1 in gridworld. In PL it should be 1

        # for a longer explanation on how this works, check out AT's
        # GridworldGameEnvironment#_get_mc_material_id_from_block_kind
        block_id = MC_MATRIAL_IDs[block_id]

        return f"[{float(x)},{float(y)},{float(z)},0.0,0.0]", {"type": block_id}
