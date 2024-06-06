"""Script to use the minecraft_eval_template_renderer in the minecraft-eval-single-agent.xml
to visualize locally the layout of the HIT.

It takes the entire XML layout and extracts only the content between the <html></html> tags.
"""

from string import Template
from typing import ClassVar
import dotenv
import os
import sys

# Project root
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# from minecraft_evaluation.minecraft_eval_game_storage import Igluminecraf_evaluationGameStorage  # noqa: E402
from minecraft_evaluation.minecraft_eval_template_renderer import SingleAgentTemplateRenderer  # noqa: E402


class HTMLSingleAgentTemplateRenderer(SingleAgentTemplateRenderer):

    def render_template(self, **template_kwargs) -> str:
        rendered_template = super().render_template(**template_kwargs)

        # Get only the HTML content of the template
        template_start_index = rendered_template.index('<html>')
        template_end_index = rendered_template.index('</html>') + len('</html>')
        return rendered_template[template_start_index:template_end_index]


def main():

    # Handpicked example with an Agent that's almost always running and that has a starting grid
    join_code = "/plaiground:join-task-with-agent ee11ab7d-ad66-4541-8dc7-5cdc0bc4c24b:89e3c063-4fb5-4ff6-833c-183d8d4809de:d1b554d4-d6b6-48e0-a28c-3ef696be46de:9e065a03-4fcf-45d8-9a03-9313f9e61e96"

    renderer = SingleAgentTemplateRenderer('../templates/minecraft-eval-single-agent-rendered.html')

    template = renderer.render_template(join_code=join_code)

    with open('../templates/minecraft-eval-single-agent.html', 'w') as test_html_hit_file:
        test_html_hit_file.write(template)


if __name__ == '__main__':
    main()
