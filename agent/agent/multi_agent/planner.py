import guidance

from guidance import gen, select
from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
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
You:
<Planner>
1. Use some tool to find the explanation of the terminology.
</Planner>

User: Find some papers about protein folding.
You:
+ keyword(text) -> papers(text)
You:
<Planner>
1. Use some tool to search for papers about protein folding.
</Planner>

User: Use my own dataset to train a saprot binary classification model. Then use my model to predict the classification of A.fasta.
You: 
+ dataset(file) -> tuned model(file)
+ test sample(text) + model(file) -> prediction(text)
You:
<Planner>
1. Use some tool to train the model. 
2. Use some tool to predict using the model path generated in the previous step.
</Planner>

User: Hi!
You: No valid protein information.
You: 
<Planner>
1. Use chat tool to make normal response.
</Planner>

Now, let's start planning for next actions.
"""


@guidance
def generation_template(lm):
    """
    Generate a thought-action template for ReAct protocol.
    Args:
        lm:  The language model object.
    """
    lm += f"""\
    <Planner>
    
    {gen(f'thought', stop='</Planner>', max_tokens=128)}
    
    </Planner>
    """
    return lm


class Planner(BaseAgent):
    """
    A sub-agent that selects a tool for the user's request.
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
            yield AgentResponse(
                content=str(response)[response_st:],
                status=AGENT_STATUS.GENERATING
            )