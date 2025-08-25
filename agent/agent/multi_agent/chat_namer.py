import guidance

from guidance import gen, select
from typing import List, Dict
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
"""


@guidance
def generation_template(lm):
    """
    Used to summarize the final answer.
    Args:
        lm:  The language model object.
    """
    lm += f"""\
    <Title>
    {gen(f'title', stop='</Title>', max_tokens=512)}
    </Title>
    """
    return lm


class ChatNamer(BaseAgent):
    """
    A sub-agent that generates responses to the user's request.
    """
    
    def __init__(self, llm):
        """
        Args:
            llm:  The language model object.
        """
        super().__init__(llm)
    
    def stream_chat(self, messages: List[Dict]):
        """
        Stream chat with the user
        Args:
            messages: Each message is a dictionary with the following keys:
                - role: The role of the speaker. Should be one of ["user", "assistant"].
                - content: The content of the message.
        """
        gen_lm = self.form_chat_template(SYSTEM_PROMPT, messages)
        response_st = len(gen_lm)
        
        stream = gen_lm.stream() + generation_template()
        for response in stream:
            # Parse the content
            content = str(response)[response_st:]
            yield AgentResponse(
                content=content,
                status=AGENT_STATUS.GENERATING
            )
