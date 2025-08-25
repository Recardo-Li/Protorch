import guidance

from guidance import gen, select
from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = f"""
You are a helpful step locator. Your function is to analyze the progress in the planning process by:
1. Marking previous task completed when their tools are sucessfully called and get a satisfactory result.
2. Evaluating completed tasks and identifying remaining ones based on the overall plan.
3. If any error occured but resolved, forget about those steps. Re-locate the current task in the overall plan.
4. If any error occured and not resolved, the current task is to explain the error to the user.
5. Clarifying and Summarizing current task.

When generating the response, you should first create the "<StepLocator>" tag. Inside this tag, you need to identify the current task by briefly describing what needs to be accomplished. After completing the description, close the tag with "</StepLocator>". Next, generate the "<CurrentTask>" tag. Within this section, provide a concise summary of the identified task, clearly outlining its core objective. Finally, close this section with the corresponding "</CurrentTask>" tag to complete the structure.

For example:
User: Find the protein sequence with uniprot id XXXX. Then predict its structure.
You: uniprot id(text) -> protein sequence(text), protein sequence(text) -> protein full atom structure(file)
You: Use uniprot_fetch_sequence
You: No result found.
<StepLocator>
You didn't find any result for the protein sequence. So the first task failed. Your task is to explain the failure to the user.
</StepLocator>
<CurrentTask>
Explain the failure to the user.
</CurrentTask>


User: What is the relationship between A.pdb and B.fasta?
You: protein full atom structure -> protein description(text), protein sequence(text) -> protein description(text), protein description(text) + protein description(text) -> comparision result(text)
You: Use protrek_protein2text to convert the protein full atom structure to protein description. Use protrek_protein2text to convert the protein sequence to protein description. Use protrek_compare to compare the protein description.
You:
<StepLocator>
The current task is to use protrek_protein2text to convert the protein full atom structure to protein description.
</StepLocator>
<CurrentTask>
Use protrek_protein2text to convert the protein full atom structure to protein description.
</CurrentTask>

User: Design an enzyme structure facilitating the reaction:  (S)-malate + NAD(+) = H(+) + NADH + oxaloacetate.
You: function description(text) -> protein sequence(text), protein sequence(text) -> protein full atom structure(file)
You: Use pinal to design the enzyme sequence. Use esmfold to predict the structure of the enzyme.
You: Used pinal and got result.
<StepLocator>
The current task is to use esmfold to predict the 3D structure of the enzyme designed by pinal. 
</StepLocator>
<CurrentTask>
Use esmfold to predict the structure of the enzyme.
</CurrentTask>

Now, let's start.
"""


@guidance
def generation_template(lm):
    """
    Generate a thought-action template for ReAct protocol.
    Args:
        lm:  The language model object.
        turn: The current turn number.
        tools: The list of available tools.

    Returns:

    """
    lm += f"""\
    <StepLocator>
    
    {gen(f'step', stop='</StepLocator>', max_tokens=128)}
    
    </StepLocator>
    
    <CurrentTask>
    
    {gen(f'current_task', stop='</CurrentTask>', max_tokens=128)}
    
    </CurrentTask>
    
    """
    return lm


class StepLocator(BaseAgent):
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
        # Generate system prompt
        gen_lm = self.form_chat_template(SYSTEM_PROMPT, messages)
        response_st = len(gen_lm)
        
        stream = gen_lm.stream() + generation_template()
        for response in stream:
            yield AgentResponse(
                content=str(response)[response_st:],
                status=AGENT_STATUS.GENERATING
            )
        
        yield AgentResponse(
            content=str(response)[response_st:],
            status=AGENT_STATUS.GENERATING,
            tool_arg={
                "current_task": response["current_task"]
            }
        )
        