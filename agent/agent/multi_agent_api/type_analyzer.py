from typing import List, Dict
from agent.agent.multi_agent.base_agent import BaseAgent
from agent.utils.constants import AGENT_STATUS, AgentResponse
from openai import OpenAI


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

User:
PUT_USER_REQUEST_HERE

You:
PUT_RESPONSE_HERE
"""


class TypeAnalyzerAPI(BaseAgent):
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
        user_request = messages[-2]["content"]
        system_prompt = SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", user_request).replace("PUT_RESPONSE_HERE", prev_response)
        input_messages = [{"role": "user", "content": system_prompt}]
        
        response = self.client.chat.completions.create(
            model="qwen-plus",
            messages=input_messages,
            stream=True,
            stop=["</TypeAnalyzer>"],
            temperature=0.0,
        )
        
        complete = ""
        for chunk in response:
            complete += chunk.choices[0].delta.content
            yield AgentResponse(
                content=complete,
                status=AGENT_STATUS.GENERATING
            )