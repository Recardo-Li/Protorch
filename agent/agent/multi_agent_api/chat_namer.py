from typing import List, Dict
from openai import OpenAI
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = """\
You are a helpful assistant for biologists conducting research. Your task is to generate a brief chat title based on the complete dialogs between the user's request and the agent's response.

Every time you generate a chat title, you must obey these rules:
1. Consider the overall dialogs and give a brief title that is informative to what the chat is about.

When you generate the chat title, output it as follows:
<Title>
Concisely generate the response.
</Title>

For example:
User: Calculate the TM-score between two proteins.
You:
After several rounds of conversation...
<Title>
TM-score calculation
</Title>

User: Design an enzyme structure facilitating the reaction:  (S)-malate + NAD(+) = H(+) + NADH + oxaloacetate.
You:
After several rounds of conversation...
<Title>
Enzyme structure design for (S)-malate + NAD(+) = H(+) + NADH + oxaloacetate
</Title>

Now, let's start giving a title for a complete chat.

User:
PUT_USER_REQUEST_HERE

You:
PUT_RESPONSE_HERE
"""


class ChatNamerAPI(BaseAgent):
    """
    A sub-agent that generates responses to the user's request.
    """
    
    def __init__(self, api_key: str):
        super().__init__(llm=None)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    
    def stream_chat(self, messages: List[Dict]):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
        """
        # Combine the user request and the previous response into the system prompt
        prev_response = messages[-1]["content"]
        user_request = messages[-2]["content"]
        system_prompt = SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", user_request).replace("PUT_RESPONSE_HERE", prev_response)
        input_messages = [{"role": "user", "content": system_prompt}]
        
        response = self.client.chat.completions.create(
            model="qwen-plus",
            messages=input_messages,
            stream=True,
            stop=["</Title>"],
            temperature=0.0,
        )

        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                content=complete,
                status=AGENT_STATUS.GENERATING
            )
        