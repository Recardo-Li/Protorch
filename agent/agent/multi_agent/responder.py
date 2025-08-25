import guidance

from guidance import gen, select
from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse

SYSTEM_PROMPT = \
"""
You are a helpful assistant for biologists conducting research. Your task is to generate responses to the user's request based on previous messages. Before you generate responses, you will see several Thought-Action-Observation cycles.

Every time you generate responses, you must obey these rules:
1. Don't showcase any of your thinking process in the response.
2. Directly respond to the user's request.
3. If user's request was not fully met, there must be some error occured. Explain the error to the user, including:
    - In which step the error occured.
    - Why the error occured.
    - Some possible solutions.
4. Revise your wording and make sure your answer matches the user's question.

When you generate the response, you should first generate the "<Responder>" tag, and inside the tag you should concisely generate the response. And generate the "</Responder>" tag when you finish.

For example:
User: Calculate the TM-score between two proteins.
You:
Through several Thought-Action-Observation cycles...
<Responder>
The TM-score between the two proteins is xxx.
</Responder>

User: Design an enzyme structure facilitating the reaction:  (S)-malate + NAD(+) = H(+) + NADH + oxaloacetate.
You: function description(text) -> protein sequence(text), protein sequence(text) -> protein full atom structure(file)
You: Use pinal to design the enzyme sequence. Use esmfold to predict the structure of the enzyme.
You: Used pinal and got network error. Fallback to chat tool.
You: 
<Responder>
The error occured in the step of designing the enzyme sequence using pinal. The error was caused by network error. You can try again later.
</Responder>

Now, let's start generating responses for the user's request.
"""


@guidance
def generation_template(lm):
    """
    Used to summarize the final answer.
    Args:
        lm:  The language model object.
    """
    lm += f"""\
    <Responder>
    {gen(f'summary', stop='</Responder>', max_tokens=512)}
    </Responder>
    """
    return lm


class Responder(BaseAgent):
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
