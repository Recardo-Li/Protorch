import guidance
import json

from guidance import gen, select
from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = """
You are a professional error handler. Your task is to adjust the tool call plan when tools fail. You have only two possible solutions:

1. Update tool arguments. If the error is caused by incorrect or incomplete parameters, suggest modifying them according to the official documentation:

PUT_TOOL_DOCUMENT_HERE

2. Fallback to default "chat" tool. If updating parameter does not work, suggest switching to the default "chat" tool.

Please follow these rules:
1. Only choose one of them each time.
2. Don't choose the same solution more than once.

When you handle the error, first generate the "<ErrorHandler>" tag. Inside the tag, you should first decide whether the failure could be resolved by adjusting parameters. Then, suggest the next step to address the issue. After completing these steps, generate the "</ErrorHandler>" tag. Following this, produce the "<solution>" tag. Inside this tag, place the name of the solution tool that addresses the error. Close the section with the corresponding "</solution>" tag upon completion.

For example:
User: I have uploaded the following files: my_data/proteins.fasta. Make alignment of the sequences.
You: 
```
action: clustalw
action_input: {"sequence_path": "proteins.fasta"}
```
You: File not found error.
You:
<ErrorHandler>
This error is caused by the incorrect file path. The full file path should be "my_data/proteins.fasta".
</ErrorHandler>
<Solution>
clustalw
</Solution>

User: Find some information about protein PXXXXX.
You:
```
action: uniprot_fetch_subsection
action_input: {"uniprot_id": "PXXXXX"}
```
You: Missing paramter subsection
You:
<ErrorHandler>
This error is caused by the missing parameter "subsection". We need to specify the subsection to fetch. According to the official documentation and chat history, the subsection should be "function".
</ErrorHandler>
<solution>
uniprot_fetch_subsection
</solution>

User: What is "Protein Secondary Structure"?
You: terminology(text) -> explanation(text)
You: Use some knowledge searching tools to find the explanation of the terminology.
You: Used wikipedia search and got a network error.
<ErrorHandler>
Network errors can't be resolved by adjusting parameters. Now fallback to the default "chat" tool.
</ErrorHandler>
<Solution>
chat
</Solution>

User: Predict the sequence of the protein.
You:
```
action: proteinmpnn
action_input: {"protein_structure": "protein"}
```
You: File not found error.
You:
<ErrorHandler>
This error is caused by the incorrect file path. However, the user didn't provide a file path. Now fall back to chat round to ask the user to provide the file path.
</ErrorHandler>
<Solution>
chat
</Solution>

Now, let's start handling the error.
"""


@guidance
def generation_template(lm, tool_list: List[str]):
    """
    Generate a thought-action template for ReAct protocol.
    Args:
        lm:  The language model object.
        tool_name: The name of the tool to call.
    """
    lm += f"""\
    <ErrorHandler>
    
    {gen('error_handler', stop = '</ErrorHandler>', max_tokens=128)}
    
    </ErrorHandler>
    
    <solution>
    
    {select(tool_list, name='solution')}
    
    </solution>
    """
    return lm


class ErrorHandler(BaseAgent):
    """
    A sub-agent that extracts arguments for a tool call.
    """
    def __init__(self, llm, tool_manager: ToolManager):
        """
        Args:
            llm:  The language model object.

            tool_manager: The tool manager object.
        """
        super().__init__(llm)
        self.tool_manager = tool_manager
    
    def stream_chat(self, messages: List[Dict], tool_name: str, tried_before: bool):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
            
            tool_name: The name of the tool to call.
        """
        # Generate system prompt
        current_tool_description = self.tool_manager.generate_document([tool_name])
        system_prompt = SYSTEM_PROMPT.replace('PUT_TOOL_DOCUMENT_HERE', current_tool_description)
        
        gen_lm = self.form_chat_template(system_prompt, messages)
        response_st = len(gen_lm)

        if not tried_before:
            tool_list = [tool_name, "chat"]
        else:
            print("Tool update has been tried before. Fallback to chat.")
            tool_list = ["chat"]
        stream = gen_lm.stream() + generation_template(tool_list)
        for response in stream:
            yield AgentResponse(
                content=str(response)[response_st:],
                status=AGENT_STATUS.GENERATING
            )
        
        # Yield tool arguments
        yield AgentResponse(
            content=str(response)[response_st:],
            status=AGENT_STATUS.GENERATING,
            tool_arg={
                "solution": response['solution']
            }
        )
        