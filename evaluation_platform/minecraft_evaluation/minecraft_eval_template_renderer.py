import html
import os
import sys
from string import Template
from typing import Any, ClassVar, Dict

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from hit_manager import TemplateRenderer


class SingleAgentTemplateRenderer(TemplateRenderer):

    def __init__(self, template_filepath: str = 'templates/') -> None:
        self.template_filepath = template_filepath

    def render_template(self, join_code, task_name, agent_name) -> str:
        # TODO add join code expiration date
        with open(self.template_filepath, 'r') as template_file:
            template = Template(template_file.read())

        template_kwargs = {
            'joinCode': join_code,
            'taskName': task_name,
            'agentName': agent_name,
        }
        # Safe substitute won't fail for missing keys. Make the renderer compatible
        # with javascript jquery
        return template.safe_substitute(**template_kwargs)


class AgentPairTemplateRenderer(TemplateRenderer):

    def __init__(self, template_filepath: str = 'templates/') -> None:
        self.template_filepath = template_filepath

    def render_template(self, join_code1, join_code2) -> str:
        # TODO add join code expiration date
        with open(self.template_filepath, 'r') as template_file:
            template = Template(template_file.read())

        template_kwargs = {
            'joinCode1': join_code1,
            'joinCode2': join_code2,
        }
        # Safe substitute won't fail for missing keys. Make the renderer compatible
        # with javascript jquery
        return template.safe_substitute(**template_kwargs)

