from typing import List

from chainlit.context import context
from chainlit.input_widget import InputWidget, Slider, TextInput
from pydantic import Field
from pydantic.dataclasses import dataclass

# Default settings
DEFAULT_MAX_ROUNDS = 50
DEFAULT_MAX_TIME = 10
DEFAULT_MAX_STALLS = 5
DEFAULT_START_PAGE = "https://bing.com"


@dataclass
class ChatSettings:
    """Useful to create chat settings that the user can change."""

    inputs: List[InputWidget] = Field(default_factory=list, exclude=True)

    def __init__(
        self,
        inputs: List[InputWidget] = None,
    ) -> None:
        if inputs is None:
            # Default settings configuration
            inputs = [
                Slider(
                    id="max_rounds",
                    label="Max Rounds",
                    initial=DEFAULT_MAX_ROUNDS,
                    min=1,
                    max=100,
                    step=1,
                    description="Maximum number of conversation rounds",
                ),
                Slider(
                    id="max_time",
                    label="Max Time (Minutes)",
                    initial=DEFAULT_MAX_TIME,
                    min=1,
                    max=60,
                    step=1,
                    description="Maximum time in minutes for task completion",
                ),
                Slider(
                    id="max_stalls",
                    label="Max Stalls Before Replan",
                    initial=DEFAULT_MAX_STALLS,
                    min=1,
                    max=10,
                    step=1,
                    description="Maximum number of stalls before replanning",
                ),
                TextInput(
                    id="start_page",
                    label="Start Page URL",
                    initial=DEFAULT_START_PAGE,
                    description="Default URL for web searches",
                ),
            ]
        self.inputs = inputs

    def settings(self):
        return dict(
            [(input_widget.id, input_widget.initial) for input_widget in self.inputs]
        )

    async def send(self):
        settings = self.settings()
        context.emitter.set_chat_settings(settings)

        inputs_content = [input_widget.to_dict() for input_widget in self.inputs]
        await context.emitter.emit("chat_settings", inputs_content)

        return settings
