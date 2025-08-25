from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from openai import OpenAI
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = f"""
You are part of a protein multi-agent system. You are a task planner agent. Your role is to convert type analysis into a complete workflow. Here are the guidelines for the conversion:
1. Break down the workflow into individual steps, where each step represents a tool call.
2. Only make one suggestion for each transition to implement the conversion.
3. Do not add any new transitions beyond what is already specified in the type analysis.
4. Make sure your suggestion number equals the conversion number in the type analysis.
5. Add some data hints to the workflow. For example, use the data generated in the first step as the input of next step.
6. For questions without specific data or information, just skip planning and return "Use chat tool to make normal response.".

When you generate the response, you should first generate the "<Planner>" tag, and inside the tag you should create a numbered list of steps involved in completing the task. Each step should clearly state the goal and the desired outcome it aims to achieve. Include additional steps as needed until all aspects of the task are covered. Once all steps have been defined, generate the corresponding "</Planner>" tag to complete the process.

For example:

User: What is "Protein Secondary Structure"?
You:
+ terminology(text) -> explanation(text)
<Planner>
1. Use some tool to find the explanation of the terminology.
</Planner>

User: Find some papers about protein folding.
You:
+ keyword(text) -> papers(text)
<Planner>
1. Use some tool to search for papers about protein folding.
</Planner>

User: Use my own dataset to train a saprot binary classification model. Then use my model to predict the classification of A.fasta.
You:
+ dataset(file) -> tuned model(file)
+ test sample(text) + model(file) -> prediction(text)
<Planner>
1. Use some tool to train the model.
2. Use some tool to predict using the model path generated in the previous step.
</Planner>

User: Hi!
You: No valid protein information.
<Planner>
1. Use chat tool to make normal response.
</Planner>

Now, let's start planning for next actions.

User:
PUT_USER_REQUEST_HERE

You:
PUT_RESPONSE_HERE
"""


class PlannerAPI(BaseAgent):
    """
    A sub-agent that selects a tool for the user's request.
    """
    
    def __init__(self, api_key: str, model="glm-4-flash"):
        super().__init__(llm=None)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        )
        self.model = model
    
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
        system_prompt = SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", user_request).replace("PUT_RESPONSE_HERE",
                                                                                             prev_response)
        input_messages = [{"role": "user", "content": system_prompt}]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=input_messages,
            stream=True,
            stop=["</Planner>"],
            temperature=0.0,
        )
        
        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                content=complete,
                status=AGENT_STATUS.GENERATING
            )