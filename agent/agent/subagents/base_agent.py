from agent.tools.tool_manager import ToolManager
from agent.llm.api import OpenAIClient


class BaseAPI:
    def __init__(self, model_name: str, tool_manager: ToolManager = None):
        """
        Args:
            model_name: The name of the api model
            tool_manager: The tool manager instance
        """
        self.client = OpenAIClient(model_name)
        self.tool_manager = tool_manager
    
    def stream_chat(self, *args, **kwargs):
        """
        Stream chat with the user
        """
        raise NotImplementedError()
