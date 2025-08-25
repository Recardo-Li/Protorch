from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from openai import OpenAI
from agent.utils.constants import AGENT_STATUS, AgentResponse

SYSTEM_PROMPT = f"""
You are a helpful step locator. Your role is to determine the current task in the overall plan by:
1. Locate yourself in the execution history. This could be easily done by looking at the number after the "Thought" tag.
2. If you are not the first step, your task is determined by the previous action.
    1. Look into the previous action, evaluate the result and determine if the action is successful. 
        - If previous action failed, give up on the plan and explain the failure to the user.
        - If previous action got expected results, mark the task as completed.
    2. Locate previous action in the overall plan.
        - If it is the last step, mark the plan as finished and set current task as sumarizing the results.
        - If it is not the last step, take the next step as current task.
3. If you are the first step, your location only depends on the overall plan.
    1. Take the first step as current task.
4. Indicate which step you are located in the overall plan if not failed or finished. 
4. Clarifying and Summarizing current task.

Previous planning and executions are placed here:
PUT_RESPONSE_HERE

When answering question, you should first create the "<StepIdentifier>" tag and indicate the current step identifier. The step identifier can be a specific step number or 'fail' or 'end'. After that close the tag with "</StepIdentifier>". Then create the "<StepLocator>" tag. Inside this tag, you need to identify the current task by briefly describing what needs to be accomplished. After completing the description, close the tag with "</StepLocator>". Next, generate the "<CurrentTask>" tag. Within this section, provide a concise summary of the identified task, clearly outlining its core objective. Finally, close this section with the corresponding "</CurrentTask>" tag to complete the structure.

For example:
User: What is the current task? Briefly explain why.
You: 
<StepIdentifier>
1
</StepIdentifier>
<StepLocator>
This is the 1st thought round as indicated by **Thought 1:**. The current task, also the 1st step in the plan, is to use protrek_protein2text to convert the protein full atom structure to protein description.
</StepLocator>
<CurrentTask>
Use protrek_protein2text to convert the protein full atom structure to protein description.
</CurrentTask>

User: What is the current task? Briefly explain why.
You: 
<StepIdentifier>
3
</StepIdentifier>
<StepLocator>
The previous action is the 2nd step, it designed an enzyme successfully. So we need to move on to the 3rd step, which is to use esmfold to predict the structure of the enzyme.
</StepLocator>
<CurrentTask>
Use esmfold to predict the structure of the enzyme.
</CurrentTask>

User: What is the current task? Briefly explain why.What is the current task?
What is the current task? Briefly explain why. 
You: 
<StepIdentifier>
fail
</StepIdentifier>
<StepLocator>
We give up on the overall plan. The previous action failed to search for uniprot proteins due to network error. The current task is to explain the network failure to the user.
</StepLocator>
<CurrentTask>
Explain the failure to the user.
</CurrentTask>

User: What is the current task? Briefly explain why.
You: 
<StepIdentifier>
end
</StepIdentifier>
<StepLocator>
Previous steps successfully finished the overall plan. The current task is to summarize previous results and respond to the user.
</StepLocator>
<CurrentTask>
Summarize previous results and respond to the user.
</CurrentTask>

Now, let's start.
"""


class StepLocatorAPI(BaseAgent):
    """
    A sub-agent that selects a tool for the user's request.
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
        system_prompt = SYSTEM_PROMPT.replace("PUT_RESPONSE_HERE",prev_response)
        input_messages = [{"role": "system", "content": system_prompt},
                          {"role": "user", "content": "What is the current task? Briefly explain why."}]
        
        response = self.client.chat.completions.create(
            model="qwen-plus",
            messages=input_messages,
            stream=True,
            stop=["</CurrentTask>"],
            max_tokens=1024,
        )

        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                    content=complete,
                    status=AGENT_STATUS.GENERATING
                )

        yield AgentResponse(
            content=complete,
            status=AGENT_STATUS.GENERATING,
            tool_arg={
                "current_task": complete.split("<CurrentTask>")[-1].split("</CurrentTask>")[0].strip()
            }
        )