import guidance

from guidance import gen, select
from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import AGENT_STATUS, AgentResponse


SYSTEM_PROMPT = f"""
You are a helpful information type conversion analyzer. Please follow these guidelines to analyze the conversions:
1. The information mainly include these categories:
- Protein sequence
- Multiple protein sequences
- Protein backbone structure
- Protein full atom structure
- Foldseek structure
- Molecular
- Protein function
- Terminology
- Dataset
- Model
- Configuration
- Other information (If you choose this type, please describe the information in detail)
- No information provided
2. Single protein sequence are usually textual strings. (e.g., "ACDEFGHIKLMNPQRSTVWY") While protein structures are usually files. SELECTION paramters are always strings. 
3. Determine the type of both input and output, including:
    - the information type (protein sequence, protein structure, protein function, etc.)
    - the entity number and relationship (one protein, multiple proteins, same protein, different proteins, etc.)
    - the string format (raw text or file path).
4. Establish necessary and least connections between different types of information to achieve the desired output. The conversions only includes:
    - Conversion within the same protein entity:
        1. protein sequence(text) -> protein full atom structure(file)
        2. protein sequence(text) -> protein function(text)
        3. protein full atom structure(file) -> foldseek sequence(text)
        4. protein full atom structure(file) -> protein sequence(text)
        5. protein backbone structure(file) -> protein sequence(text)
        5. functional description(text) -> protein sequence(text)
        6. PDB ID(text) -> structure(file)
        7. uniprot ID(text) -> protein sequence(text)/structure(file)/function(text)
        

    - For multiple protein entities, mostly we do search/comparison:
        1. protein sequence(text) + protein sequence(text) -> comparision result(text/file)
        2. protein full atom structure(file) + protein full atom structure(file) -> comparision result(text)
        3. protein function(text) + protein function(text) -> comparision result(text)
        4. protein sequence(text)/structure(file)/function(text) -> search result of protein sequence(text)/structure(file)/function(text)
    
    - Specially, We can do unconditional generation:
        1. -> protein backbone structure(file)
    
    - We can also proceed maching learning workflow:
        1. Dataset(file) + Configuration(text) -> Trained Model(file)
        2. Test sample(text) + Model(file) -> Prediction(text)
5. If no valid protein related information is provided, use "No valid protein information".

When you generate the response, you should first generate the "<TypeAnalyzer>" tag, and inside the tag you should
determine the information type of the input and output and connect them by "->". Add some bridge if needed. Annotate the 
information type with string type(text/file). And generate the "</TypeAnalyzer>" tag when you finish.

For example:
User: What is the relationship between A.pdb and B.fasta?
You:
<TypeAnalyzer>
+ protein1 full atom structure -> protein1 description(text)
+ protein2 sequence(text) -> protein2 description(text)
+ protein1 description(text) + protein2 description(text) -> comparision result(text)
</TypeAnalyzer>

User: Design an enzyme structure facilitating the reaction:  (S)-malate + NAD(+) = H(+) + NADH + oxaloacetate.
You:
<TypeAnalyzer>
+ function description(text) -> protein sequence(text)
+ protein sequence(text) -> protein full atom structure(file)
</TypeAnalyzer>

User: Design an antibody of A.pdb.
You:
<TypeAnalyzer>
+ protein full atom structure(file) -> antibody full atom structure(file)
+ antibody full atom structure(file)-> optimized antibody full atom structure(file)
</TypeAnalyzer>

User: What is "Protein Secondary Structure"?
You:
<TypeAnalyzer>
+ terminology(text) -> explanation(text)
</TypeAnalyzer>

User: Find literatures about P12345.
You:
<TypeAnalyzer>
+ UniProt ID(text) -> protein sequence(text)
+ protein sequence(text) -> protein description(text)
+ protein description(text) -> literature(text)
</TypeAnalyzer>

User: Use my own dataset to train a saprot binary classification model. Then use my model to predict the classification of AAAAAAAA
You:
<TypeAnalyzer>
+ dataset(file) -> trained model(file),
+ protein sequence(text) + model(file) -> prediction(text)
</TypeAnalyzer>

User: Hi!
You:
<TypeAnalyzer>
No valid protein information.
</TypeAnalyzer>

Now, let's start analyzing the information type.
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
    <TypeAnalyzer>
    
    {gen(f'thought', stop='</TypeAnalyzer>', max_tokens=128)}
    
    </TypeAnalyzer>
    
    """
    return lm


class TypeAnalyzer(BaseAgent):
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