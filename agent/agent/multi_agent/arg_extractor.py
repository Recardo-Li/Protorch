import guidance
import json

from guidance import gen, select
from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = """
You are a helpful tool argument extractor. Your task is to extract arguments from previous chat messages to call a tool. Here is the description of the tools you can call:

PUT_TOOL_DESCRIPTION_HERE

Every time you extract arguments, you must follow these rules:
1. Check tool requirements first:
   - Determine whether the tool needs any parameters.  
   - If no inputs are required, skip the extraction step entirely. 

2. Find all inputs:
Look through previous messages to collect every input the tool asks for, including both the required and optional ones.

3. Check input formats:
Confirm each input matches the correct type (e.g., file/text). If not, don't use it.

4. Keep file paths EXACTLY as written:
For files like "STRUCTURE", "FASTA", or "DATASET" - use the path EXACTLY as mentioned, don't change it.

5. Guess missing info from the conversation:
For parameters like "quetsion" or "keywords", they are usually pulled from the user's messages and previous tool call history.

6. Decide when to run the tool:
Only run the tool if ALL REQUIRED PARAMETERS ARE FOUND
If you're missing anything, use "chat" tool and explain which arguments are missing.

Follow this format when displaying extracted arguments:
<ArgumentExtractor>
Check which arguments are needed and explain where you will extract the arguments. 
</ArgumentExtractor>
```
action: The tool name
action_input: {"arg1": "value1", "arg2": "value2", ...}
```

Ensure all arguments are formatted as key-value pairs with double quotes around both keys and string values, following strict JSON syntax. And make sure your markdown code block is closed with three backticks.

For example:
User: Predict the structure of "AAAAAAAA" using ESMFold.
You: I choose to call the tool "esmfold".
<ArgumentExtractor>
The tool "esmfold" is called. It requires a protein sequence. The sequence could be extracted from user input.
</ArgumentExtractor>
```
action: esmfold
action_input: {"protein_sequence": "AAAAAAAA"}
```

User: Call the tool TMalign.
You: I choose to call the tool "tmalign".
<ArgumentExtractor>
The tool "tmalign" is called. It requires two PDB files to align. However, previous messages don't contain any arguments. So use "chat" tool to ask for the arguments.
</ArgumentExtractor>
```
action: chat
action_input: {}
```

User: Who are you?
You: I choose to call the tool "chat".
<ArgumentExtractor>
This tool "chat" is called. It doesn't require any arguments. No extraction is needed.
</ArgumentExtractor>
```
action: chat
action_input: {}
```

Now, let's start extracting arguments for the tool.
"""


@guidance
def generation_template(lm, tool_name: str):
    """
    Generate a thought-action template for ReAct protocol.
    Args:
        lm:  The language model object.
        tool_name: The name of the tool to call.
    """
    lm += f"""\
    <ArgumentExtractor>
    
    The tool "{tool_name}" is called.{gen(f'thought', stop='</ArgumentExtractor>', max_tokens=128)}
    </ArgumentExtractor>
    
    ```
    action: {select([tool_name, "chat"], name='action')}
    action_input: {gen('action_input', stop='```')}
    ```
    """
    return lm


class ArgumentExtractor(BaseAgent):
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
    
    def stream_chat(self, messages: List[Dict], tool_name: str):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
            
            tool_name: The name of the tool to call.
        """
        # Generate system prompt
        tool_description = self.tool_manager.generate_argument_document(tool_name)
        system_prompt = SYSTEM_PROMPT.replace('PUT_TOOL_DESCRIPTION_HERE', tool_description)
        
        gen_lm = self.form_chat_template(system_prompt, messages)
        response_st = len(gen_lm)

        stream = gen_lm.stream() + generation_template(tool_name)
        for response in stream:
            yield AgentResponse(
                content=str(response)[response_st:],
                status=AGENT_STATUS.GENERATING
            )
        
        # Yield tool arguments
        tool_name = response['action']
        action_input = json.loads(response['action_input'])
        tool_arg = {
            "name": tool_name,
            "args": action_input
        }
        yield AgentResponse(
            content=str(response)[response_st:],
            status=AGENT_STATUS.GENERATING,
            tool_arg=tool_arg
        )
        