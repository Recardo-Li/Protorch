from typing import List, Dict
from openai import OpenAI
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

User:
PUT_USER_REQUEST_HERE

You:
PUT_RESPONSE_HERE
"""


class ErrorHandlerAPI(BaseAgent):
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
        tool_name = tool_name.strip()
        current_tool_description = self.tool_manager.generate_document([tool_name])
        system_prompt = SYSTEM_PROMPT.replace('PUT_TOOL_DOCUMENT_HERE', current_tool_description)
        
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
            stop=["</Solution>"],
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
        solution = complete.split("<Solution>")[-1].split("</Solution>")[0]
        yield AgentResponse(
            content=complete,
            status=AGENT_STATUS.GENERATING,
            tool_arg={
                "solution": solution
            }
        )