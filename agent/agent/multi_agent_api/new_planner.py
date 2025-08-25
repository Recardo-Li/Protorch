from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from openai import OpenAI
from agent.utils.constants import AGENT_STATUS, AgentResponse
from agent.tools.tool_manager import ToolManager


SYSTEM_PROMPT = """ \
You are a helpful planner. Your task is to decompose the user's request into a series of steps that can be executed by
different tools.
 
All tools you can call are described here:
PUT_TOOL_DESCRIPTION_HERE

When you decompose the user's request, each single step you must choose one tool to call. You should describe the goal
of each step, the tool you will use and the output of the step. You should follow the format below:

<Planner>
{
    “user_request": "user's request",
    "1": {
            "tool": "xxx",
            "goal": "xxx",
        },
    "2": {
            "tool": "yyy",
            "goal": "yyy",
        },
    "3": {
            "tool": "zzz",
            "goal": "zzz",
        },
}
</Planner>

Now, let's start planning.

User: PUT_USER_REQUEST_HERE
"""


class NewPlannerAPI(BaseAgent):
    """
    A sub-agent that selects a tool for the user's request.
    """
    
    def __init__(self, api_key: str, tool_manager: ToolManager, model="glm-4-flash"):
        super().__init__(llm=None)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        )
        self.model = model
        self.tool_manager = tool_manager
    
    def stream_chat(self, messages: List[Dict]):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
        """
        user_request = messages[-1]["content"]
        
        # Get tool description
        all_tools = list(self.tool_manager.tools)
        tool_desc = self.tool_manager.generate_document(all_tools)
        system_prompt = SYSTEM_PROMPT.replace("PUT_TOOL_DESCRIPTION_HERE", tool_desc)
        system_prompt = system_prompt.replace("PUT_USER_REQUEST_HERE", user_request)

        input_messages = [{"role": "system", "content": system_prompt}] + messages
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=input_messages,
            stream=True,
            stop=["</Planner>"],
            temperature=0.0,
        )
        
        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                content=complete,
                status=AGENT_STATUS.GENERATING
            )