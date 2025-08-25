from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from openai import OpenAI
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = """\
You are a fair evaluator to assess whether a generated response meets the user's request. Given a user's request and a
generated response, you need to evaluate the response based on the following rules:
1. If the user is clearly asking something, whether the response directly answers the user's request.
2. If the user's request is ambiguous, whether the response provides a reasonable answer.

When you generate your evaluation result, you should first generate the "<Evaluation>" tag, and inside the tag you
should give your detailed analysis and generate the "</Evaluation>" tag when you finish. After that, you should generate
the "<Decision>" tag, and inside the tag you should output "yes" when the response meets the user's request, and
"no" when the response does not meet the user's request. Finally, you should generate the "</Decision>" tag.

For example:
User: Calculate the TM-score between two proteins.
Response: After calculating the TM-score, I got the result of 0.85.
You:
<Evaluation>
The user is asking for a TM-score calculation between two proteins, and the response provides the corresponding result.
So the response meets the user's request.
</Evaluation>
<Decision>
yes
</Decision>

User: Predict the structure.
Response: Please provide the sequence of the protein for structure prediction.
You:
<Evaluation>
The user is asking for a structure prediction, but does not provide the sequence of the protein. The response provides a
reasonable answer by asking for the sequence. So the response meets the user's request.
</Evaluation>
<Decision>
yes
</Decision>

User: Predict the structure of the protein "AESDFASDF".
Response: CUDA out of memory. Please try again later.
You:
<Evaluation>
The user is asking for a structure prediction and provides the sequence of the protein. However, the response does not
provide the generated structure. So the response does not meet the user's request.
</Evaluation>
<Decision>
No
</Decision>

Now, let's start the evaluation.

User:
PUT_USER_REQUEST_HERE

You:
PUT_RESPONSE_HERE
"""


class EvaluatorAPI(BaseAgent):
    """
    A sub-agent that generates responses to the user's request.
    """
    
    def __init__(self, api_key: str, model="glm-4-flash"):
        super().__init__(llm=None)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        )
        self.model = model
    
    def stream_chat(self, user_request: str, response: str):
        """
        Evaluate the response based on the user's request.
        Args:
            user_request: The user's request.
            response: The generated response.
        """
        system_prompt = SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", user_request).replace("PUT_RESPONSE_HERE",
                                                                                             response)
        input_messages = [{"role": "user", "content": system_prompt}]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=input_messages,
            stream=True,
            stop=["</Decision>"],
            temperature=0.0,
        )
        
        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                content=complete,
                status=AGENT_STATUS.GENERATING
            )
