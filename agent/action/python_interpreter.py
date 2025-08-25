# flake8: noqa: E501
import io
from contextlib import redirect_stdout

from lagent.actions.base_action import BaseAction, tool_api


class PythonInterpreter(BaseAction):
    """
    Python interpreter to execute Python code.
    """
    @tool_api
    def run(self, command: str) -> dict:
        """
        Run Python code and return the output. You must obey the following rules to write the code:
        - Import all the necessary libraries.
        - Define all variables and functions to be used.
        - Avoid writing long code in a single line. Each line should only execute one statement.
        - Use "print" to display all the outputs

        Args:
            command (str): Python code to be executed.

        Returns:
            dict
                - output (str): Output of the code execution.

        """

        # A string stream to capture the outputs of exec
        output = io.StringIO()
        try:
            # Redirect stdout to the StringIO object
            with redirect_stdout(output):
                # Allow imports
                exec(command, globals())

        except Exception as e:
            # If an error occurs, capture it as part of the output
            print(f"Error: {e}", file=output)

        # Close the StringIO object and return the output
        value = output.getvalue()
        output.close()
        return {"output": value}
    