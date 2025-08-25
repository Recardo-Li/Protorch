from lagent.actions.base_action import BaseAction, tool_api

class YourTool(BaseAction):
    @tool_api
    def run(self, params: dict) -> dict:
        """
        Describe your tool here.

        Args:
            params(dict) : Describe your parameters here.

        Returns:
            output: Explain what the output is.
        """
        # Add your code here
        pass
        
        return {"output": "output here"}
