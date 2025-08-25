from typing import List, Dict
from openai import OpenAI
from agent.agent.subagents.base_agent import BaseAPI
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = """\
You are a helpful summarizer. Your task is to generate a brief chat title for a conversation between the user and the
assistant.

The user request is here:
===
PUT_USER_REQUEST_HERE
===

The assistant response is here:
===
PUT_RESPONSE_HERE
===

You should generate the plan in the following format: First generate a "<Title>" tag, then generate the title in
JSON format, and finally generate a "</Title>" tag. Remember your sender name is "namer". An example is shown below:

<Title>
{
    "sender": "namer",
    "content": "Chat title"
}
</Title>

Now, let's start generating the chat title.
"""


class Titler(BaseAPI):
    """
    A sub-agent that generates responses to the user's request.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def stream_chat(self, user_request: str, response: str):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
        """
        system_prompt = SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", user_request)
        system_prompt = system_prompt.replace("PUT_RESPONSE_HERE", response)
        input_messages = [{"role": "user", "content": system_prompt}]
        
        response = self.client.call_openai(
            messages=input_messages,
            stream=True,
            temperature=0.001,
        )

        complete = ""
        for chunk in response:
            content = "" if chunk.choices[0].delta is None else chunk.choices[0].delta.content or ""
            complete += content
            yield AgentResponse(
                content=complete,
                status=AGENT_STATUS.GENERATING
            )
        
        # Return the plan as a dictionary
        content = complete.split("<Title>")[-1].split("</Title>")[0]
        yield AgentResponse(
            content=content,
            status=AGENT_STATUS.GENERATING
        )
        