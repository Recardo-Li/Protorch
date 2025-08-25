import guidance

from guidance import gen, select
from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = f"""
You are a helpful tool selector. Your task is to select the most appropriate tool for the current task. 
When selecting a tool, follow these guidelines:
1. Select a tool that can complete the current task.
2. Check the parameters and the types, make sure all neccessary parameters are provided in user's query. If not, consider selecting another tool.
3. If you can't find a suitable tool, call the default "chat" tool.
4. If the task have been completed or could not be completed, you can call the default "chat" tool.
5. You can only use the tools listed below. You can't use any other tools that are not listed.

All available tools are listed below:

PUT_TOOL_DESCRIPTION_HERE

When you select a tool to perform the task, you should first generate the "<ToolSelector>" tag. Inside this tag, you must choose a tool capable of completing the current task and briefly explain the reason for your selection. After completing this, generate the "</ToolSelector>" tag to close the section. Following this, you must generate the "<tool>" tag, place the name of the selected tool inside it, and then close the tag with "</tool>".

For example:
User: Who are you?
You:
<ToolSelector>
The "chat" tool is selected because the user is asking a general question.
</ToolSelector>
<tool>
chat
</tool>

User: De novo design a protein.
You: 
<ToolSelector>
This is an unconditional protein design task. The rfdiffusion tool is selected.
</ToolSelector>
<tool>
rfdiffusion
</tool>

User: Use the tool cif2pdb to convert a CIF file to a PDB file.
You:
<ToolSelector>
I don't have a tool to do the conversion. So I will call the "chat" tool to respond to the user's request.
</ToolSelector>
<tool>
chat
</tool>

Now, let's start selecting tools for the user's request.
"""


@guidance
def generation_template(lm, tools: List[str]):
    """
    Generate a thought-action template for ReAct protocol.
    Args:
        lm:  The language model object.
        turn: The current turn number.
        tools: The list of available tools.

    Returns:

    """
    lm += f"""\
    <ToolSelector>
    
    {gen(f'thought', stop='</ToolSelector>', max_tokens=128)}
    
    </ToolSelector>
    
    <tool>
    
    {select(tools, name='tool_name')}
    
    </tool>
    """
    return lm


class ToolSelector(BaseAgent):
    """
    A sub-agent that selects a tool for the user's request.
    """
    def __init__(self, llm, tool_manager: ToolManager):
        """
        Args:
            llm:  The language model object.
            
            tool_manager: The tool manager object.
        """
        super().__init__(llm)
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
        system_prompt = SYSTEM_PROMPT.replace('PUT_TOOL_DESCRIPTION_HERE', tool_description)
        
        gen_lm = self.form_chat_template(system_prompt, messages)
        response_st = len(gen_lm)
        
        stream = gen_lm.stream() + generation_template(self.tool_manager.tools.keys())
        for response in stream:
            # Parse the content
            # content = str(self.response)[response_st:]
            # if content.startswith("<explanation>"):
            #     content = content.split("<explanation>", 1)[-1].rsplit("</explanation>", 1)[0].strip()
            # else:
            #     content = ""
                
            yield AgentResponse(
                content=str(response)[response_st:],
                status=AGENT_STATUS.GENERATING
            )
        
        yield AgentResponse(
            content=str(response)[response_st:],
            status=AGENT_STATUS.GENERATING,
            tool_arg={
                "name": response["tool_name"]
            }
        )
        