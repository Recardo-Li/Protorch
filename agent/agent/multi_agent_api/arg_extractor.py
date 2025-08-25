import ast
import json

from openai import OpenAI
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

When you display the extracted arguments, you should first generate the "<ArgumentExtractor>" tag. After the tag, you need to:
1. Determine which arguments are required for the task
2. Explicitly state the source locations where each argument will be extracted from
3. Describe the extraction process in a clear manner
Then, generate the "</ArgumentExtractor>" tag to conclude this section.
After completing the ArgumentExtractor section, generate the corresponding action structure as follows:
```
action: The tool name
action_input: {"arg1": "value1", "arg2": "value2", ...}
```
Ensure all arguments are formatted as key-value pairs with double quotes around both keys and string values, following strict JSON syntax. And make sure your markdown code block is closed with three backticks.

For example:
User: Predict the structure of "AAAAAAAA" using ESMFold.
You:
<ArgumentExtractor>
The tool "esmfold" is called. It requires a protein sequence. The sequence could be extracted from user input.
</ArgumentExtractor>
```
action: esmfold
action_input: {"protein_sequence": "AAAAAAAA"}
```

User: Call the tool TMalign.
You:
<ArgumentExtractor>
The tool "tmalign" is called. It requires two PDB files to align. However, previous messages don't contain any arguments. So use "chat" tool to ask for the arguments.
</ArgumentExtractor>
```
action: chat
action_input: {}
```

User: Who are you?
You:
<ArgumentExtractor>
This tool "chat" is called. It doesn't require any arguments. No extraction is needed.
</ArgumentExtractor>
```
action: chat
action_input: {}
```

Now, let's start extracting arguments for the tool.

User:
PUT_USER_REQUEST_HERE

You:
PUT_RESPONSE_HERE
"""


class ArgumentExtractorAPI(BaseAgent):
    """
    A sub-agent that extracts arguments for a tool call.
    """
    
    def __init__(self, api_key: str, tool_manager: ToolManager):
        """
        Args:
            tool_manager: The tool manager object.
        """
        super().__init__(llm=None)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
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
        tool_name = tool_name.strip()
        tool_description = self.tool_manager.generate_argument_document(tool_name)
        system_prompt = SYSTEM_PROMPT.replace('PUT_TOOL_DESCRIPTION_HERE', tool_description)
        
        # Combine the user request and the previous response into the system prompt
        prev_response = messages[-1]["content"]
        user_request = messages[-2]["content"]
        system_prompt = system_prompt.replace("PUT_USER_REQUEST_HERE", user_request).replace("PUT_RESPONSE_HERE",
                                                                                             prev_response)
        input_messages = [{"role": "user", "content": system_prompt}]
        response = self.client.chat.completions.create(
            model="qwen-plus",
            messages=input_messages,
            stream=True,
            temperature=0.0,
        )
        
        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                content=complete,
                status=AGENT_STATUS.GENERATING
            )
        
        # Yield tool arguments
        tool_info = complete.split("```")[1].strip()
        tool_name, tool_args = tool_info.split("\n", 1)
        tool_name = tool_name.split(":", 1)[1].strip()
        action_input = json.loads(tool_args.split(":", 1)[1].strip())
        
        
        tool_arg = {
            "name": tool_name,
            "args": action_input
        }
        
        yield AgentResponse(
            content=complete,
            status=AGENT_STATUS.GENERATING,
            tool_arg=tool_arg
        )
        