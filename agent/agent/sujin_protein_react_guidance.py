import guidance
import json

from guidance import gen, select
from data.raw_input import RawInput
from typing import List, Dict
from transformers import AutoTokenizer
from agent.agent.utils import *
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse

SYSTEM_PROMPT = \
"""
You are a helpful assistant for biologists conducting research. Your insights are well-considered, and you take responsibility for your words, as they derive from external knowledge bases and tools. With these resources, you excel at answering protein-related questions and handling computational biology tasks. The specific tools you can use are listed below:

PUT_TOOL_DESCRIPTION_HERE

You must obey the following rules:
1. Only use available tools when explicitly requested by the user or when the task requires it.
2. Once a task is completed using a tool, cease further tool usage unless additional steps are needed.
3. Do not use the Python interactive environment unless the user specifically asks for it.
4. If a tool call returns only a success status (e.g., without detailed output), end the chat promptly.
When you generate responses, you will go through several Thought-Action-Observation cycles.
You should use the following template for each cycle:
Thought 1:
**Think what to do next and whether to use a tool or not. Output in one line**
Action 1:
```
action: The tool name
action_input: The required parameters
```
Observation 1:
```
The result after using the tool
```
Finally, if you know the final answer, output it as follows:
Finish:
**Output the final answer in one line. Don't output any newlines!**
"""


@guidance
def thought_action_template(lm, turn, tools: List[str]):
    """
    Generate a thought-action template for ReAct protocol.
    Args:
        lm:  The language model object.
        turn: The current turn number.
        tools: The list of available tools.

    Returns:

    """
    lm += f"""\
    Thought {turn + 1}:
    **I{gen(f'thought', stop='**')}**\n
    Action {turn + 1}:
    ```
    action: {select(tools, name='action')}
    action_input: {{{gen('action_input', stop='}')}}}
    ```
    """
    return lm


class ProteinReActAgent:
    """
    An implementation of ReAct (https://arxiv.org/abs/2210.03629).
    """
    def __init__(self,
                 model_path: str,
                 tool_manager: ToolManager,
                 max_turn: int = 4):
        """
        Args:
            model_path:  The path to the language model.
            tool_manager: The tool manager object.
            max_turn: The maximum number of turns.
        """

        self.max_turn = max_turn
        self.llm = guidance.models.Transformers(model_path, device_map="auto", echo=False)
        self.tool_manager = tool_manager
        # self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Variables for response generation
        self.gen_lm = None
        self.tmp_lm = None
        self.response = None
        self.action = None
        self.action_input = None

    def change_tool_call(self, tool_name: str, tool_args: dict):
        """
        Change the tool call
        Args:
            tool_name: Changed tool name
            tool_args: Changed tool arguments
        """
        self.action = tool_name
        self.action_input = tool_args
    
    def stream_chat(self, messages: List[Dict]):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
        """
        
        # Generate system prompt
        selected_tools = self.tool_manager.retrieve(messages[0]["content"])
        tool_description = self.tool_manager.generate_document(selected_tools)
        system_prompt = SYSTEM_PROMPT.replace('PUT_TOOL_DESCRIPTION_HERE', tool_description)
        with guidance.system():
            self.gen_lm = self.llm + system_prompt
        
        for message in messages:
            with eval(f"guidance.{message['role']}()"):
                self.gen_lm += message["content"]
        
        # Add response prefix
        self.gen_lm += self.llm.chat_template.get_role_start("assistant")
        self.tmp_lm = self.gen_lm
        response_st = len(self.gen_lm)
        
        ###############################################
        #               ReAct process                 #
        ###############################################
        for i, turn in enumerate(range(self.max_turn)):
            ###############################################
            #                   Think                     #
            ###############################################
            stream = self.tmp_lm.stream() + thought_action_template(i, self.tool_manager.tools.keys())
            for self.response in stream:
                yield AgentResponse(
                    content=str(self.response)[response_st:],
                    status=AGENT_STATUS.GENERATING
                )
                
            self.tmp_lm = self.gen_lm + str(self.response)[response_st:]
            
            self.action = self.response["action"]
            self.action_input = json.loads(f"{{{self.response['action_input']}}}")
            
            # Change the agent status to TOOL_CALLING
            yield AgentResponse(
                content=str(self.response)[response_st:],
                status=AGENT_STATUS.TOOL_CALLING,
                tool_arg={
                    "name": self.action,
                    "args": self.action_input
                }
            )

            # Users may modify the tool call at the frontend
            modified_tool_call = f"```\naction: {self.action}\n" \
                                 f"action_input: {json.dumps(self.action_input, indent=4)}\n```\n"
            origin_content = str(self.response)[response_st:].rsplit("```", 2)[0]
            self.response = origin_content + modified_tool_call
            self.tmp_lm = self.gen_lm + origin_content + modified_tool_call

            # Change the agent status to TOOL_RUNNING
            yield AgentResponse(
                content=self.response,
                status=AGENT_STATUS.TOOL_RUNNING,
                tool_arg={
                    "name": self.action,
                    "args": self.action_input
                }
            )

            # If the action is "chat", break the loop
            if self.action == "chat":
                break

            ###############################################
            #                  Action                     #
            ###############################################
            # obs = self.tool_manager.call(self.action, self.action_input)
            for obs in self.tool_manager.call(self.action, self.action_input):
                added_prompt = f"Observation {i + 1}:\n```\n{obs}\n```\n"
                yield AgentResponse(
                    content=self.response+added_prompt,
                    status=AGENT_STATUS.GENERATING
                )
            
            ###############################################
            #                 Observation                 #
            ###############################################
            # added_prompt = f"Observation {i + 1}:\n```\n{obs}\n```\n"
            self.tmp_lm += added_prompt
        
        ###############################################
        #                Final response               #
        ###############################################
        yield AgentResponse(
            content="",
            status=AGENT_STATUS.FINAL_RESPONSE,
        )
            
        stream = self.tmp_lm.stream() + f"Finish:\n**{gen('finish', stop='**')}**\n"
        for self.response in stream:
            yield AgentResponse(
                content=str(self.response)[response_st:],
                status=AGENT_STATUS.GENERATING
            )

        # Change the agent status to IDLE
        yield AgentResponse(
            content=str(self.response)[response_st:],
            status=AGENT_STATUS.IDLE
        )
