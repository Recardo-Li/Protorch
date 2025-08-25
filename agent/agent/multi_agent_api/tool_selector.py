import guidance


from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse
from openai import OpenAI



SYSTEM_PROMPT = f"""
You are a helpful tool selector. Your task is to select the most appropriate tool for the current task. 
When selecting a tool, follow these guidelines:
1. Select a tool that can complete the current task.
2. Check the parameters and the types, make sure all necessary parameters are provided. If not, consider selecting another tool.
3. If you can't find a suitable tool, call the default "chat" tool.
4. If the task have been completed or could not be completed, you can call the default "chat" tool.
5. If the task is only demonstration, you can call the default "chat" tool.
6. You can only use the tools listed below. You can't use any other tools that are not listed.
7. Use EXACTLY the same name as the tool listed below.

All available tools are listed below:

PUT_TOOL_DESCRIPTION_HERE

The Available toolnames are:

PUT_TOOLNAMES_HERE

The task is:

PUT_TASK_HERE

When you answer the question, you should first generate the "<ToolSelector>" tag. Inside this tag, you must choose a tool capable of completing the current task and BRIEFLY explain the reason for your selection. After completing this, generate the "</ToolSelector>" tag to close the section. Following this, you must generate the "<tool>" tag, place the name of the selected tool inside it, and then close the tag with "</tool>".

For example:
User: Now select a tool.
You:
<ToolSelector>
The "chat" tool is selected because the curent task is to respond to the user's greeting.
</ToolSelector>
<tool>
chat
</tool>

User: Now select a tool.
You:
<ToolSelector>
This is an unconditional protein design task. The rfdiffusion tool is selected.
</ToolSelector>
<tool>
rfdiffusion
</tool>

User: Now select a tool.
You:
<ToolSelector>
I don't have a tool to do the conversion. So I will call the "chat" tool to respond to the user's request.
</ToolSelector>
<tool>
chat
</tool>

Now, let's start selecting tools for current task.
"""


class ToolSelectorAPI(BaseAgent):
    """
    A sub-agent that selects a tool for the user's request.
    """
    def __init__(self, api_key: str, tool_manager: ToolManager):
        super().__init__(llm=None)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.tool_manager = tool_manager
        
    def stream_chat(self, messages: List[Dict], current_task: str):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
        """
        # Generate system prompt
        selected_tools = self.tool_manager.retrieve(current_task, top_k=15)
        tool_description = self.tool_manager.generate_document(selected_tools)
        system_prompt = SYSTEM_PROMPT.replace('PUT_TOOL_DESCRIPTION_HERE', tool_description).replace('PUT_TOOLNAMES_HERE', ','.join(selected_tools)).replace('PUT_TASK_HERE', current_task)
        
        
        input_messages = [{"role": "system", "content": system_prompt},
                          {"role": "user", "content": f"The current task is to {current_task}. Now select a tool."}]
        
        response = self.client.chat.completions.create(
            model="qwen-plus",
            messages=input_messages,
            stream=True,
            stop=["</tool>"]
        )

        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                    content=complete,
                    status=AGENT_STATUS.GENERATING
                )

        yield AgentResponse(
            content=complete,
            status=AGENT_STATUS.GENERATING,
            tool_arg={
                "name": complete.split("<tool>")[-1].split("</tool>")[0].strip()
            }
        )
        