from lagent.actions.base_action import BaseAction, tool_api


class ChatAction(BaseAction):
    @tool_api
    def run(self) -> None:
        """
        This tool is used in many normal cases:
        1. Reply to normal greetings.
        2. Reply to any questions about all tools you have.
        2. Reply to any simple questions about common sense or general knowledge.
        4. Any other cases that you don't need to call other tools.
        """
        return