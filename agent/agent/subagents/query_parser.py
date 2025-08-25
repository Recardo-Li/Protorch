import json
import json_repair

from agent.utils.constants import AGENT_STATUS, INPUT_FLOW_ARG_DESCRIPTION, OUTPUT_FLOW_ARG_DESCRIPTION, TOOL_SPECIFIC_ARG_DESCRIPTION, CONFIGURATIVE_ARG_DESCRIPTION, AgentResponse
from agent.agent.subagents.base_agent import BaseAPI
from agent.tools.type_check import type_check


SYSTEM_PROMPT = """ \
You are an expert Query Parser agent. Your primary task is to parse a user's request to identify the necessary inputs and the expected outputs for downstream tool calls.

You will be provided with the following context for each request:

1. Available Input Types: A list of all possible input arguments for the tools.
===
PUT_INPUT_TOOL_ARG_DESCRIPTION_HERE
===

2. Available Output Types: A list of all possible outputs the tools can generate.
===
PUT_OUTPUT_TOOL_ARG_DESCRIPTION_HERE
===

3. Feedback on Previous Attempts (Optional): An analysis of your previous responses for this request, which you must use to correct your new response.
===
PUT_PREVIOUS_RESPONSES_HERE
===

You must follow these rules when parsing the user's request:

1. For inputs, extract the specific values from the request. For outputs, identify the type of the expected result.

2. You must group all inputs and outputs according to the conceptual entity they belong to.
- Naming Convention: Use standardized names: protein_1, protein_2, etc.
- Same Entity Logic: When an input and its corresponding output refer to the same object, they must share the same entity ID.
    * Example: For "predict the structure of protein X," the input AA_SEQUENCE for protein X and the output STRUCTURE_PDB for protein X both belong to protein_1.
- Different Entity Logic: When an input and output refer to different objects, they must have different entity IDs.
    * Example 1 (Binder Design): For "design a binder for target protein Y," the input PDB_ID for target Y belongs to protein_1, while the resulting output STRUCTURE_PATH is a new entity, protein_2.
    * Example 2 (Scaffold Design): For "design a 20aa loop on scaffold Z," the input STRUCTURE_PATH for scaffold Z belongs to protein_1, while the resulting output STRUCTURE_PATH is a new entity, protein_2.
- General Items: Assign any non-protein-specific parameters to the general entity.

3. Differentiate between semantic extraction (e.g., for TEXT, QUESTION) and literal extraction (e.g., for AA_SEQUENCE, FASTA_PATH).

4. Some terminolgies can be categorized into UNIPROT_SUBSECTION to extract specific subsections of a protein from the Uniprot database. These subsections include:
    - Domains
    - Topology
    - PTMs
    - Function
    - Disease/Biotech
    - Genetics

5. For other terminologies that are not included in our supported types, extract them as TEXT inputs. Each terminology should be a few short keywords. Extract them as much as possible and as short as possible. Protein related terminologies should be assigned to their protein entity, while others should be assigned to the general entity.

6. If an input is ambiguous (e.g., an unknown ID), list all possible types it could be (e.g., UNIPROT_ID, PDB_ID, PFAM_ID).

7. Sometimes the same type have different semantical meanings, notice them in the "analysis" field of the response. (e.g. "STRUCTURE_PATH" can be used to represent the full atomic structure of a protein, or a backbone-only structure; "AA_SEQUENCE" can be used to represent the full sequence of a protein, or a domain sequence of a protein, etc.)

8. If PREVIOUS_RESPONSES are provided, analyze them to correct your response.
- Incorrect Type: If a previous attempt identified an ID as PDB_ID and it was incorrect, try alternative types like UNIPROT_ID in your new response.
- Incorrect Format: If a previous attempt failed due to an invalid format (e.g., for RFDIFFUSION_CONTIGS), re-evaluate the request against the type definition. If no specific value can be confidently extracted, use an empty string '' as the value.

When you generate response, you must follow this format: First generate a "<QueryParser>" tag, then generate responses
in JSON format, and finally generate a "</QueryParser>" tag. An example of the response is shown below, where the key
is the input type and the value is a list of values (if no available input types, just generate an empty content dict):

<QueryParser>
{
    "sender": "query_parser",
    "analysis": "analysis the most related tasks and the expected input and output of the tasks. If previous responses are provided, analysis on the reasons of wrong identifications.",
    "content": {
        "input": {
            "protein_1": {
                "input_type_1": ["value_1"],
                "input_type_2": ["value_2", "value_3"]
            },
            "protein_2": {
                "input_type_3": ["value_4"],
                "input_type_4": ["value_5"]
            },
            "general": {
                "input_type_5": ["value_6"]
            }
        },
        "output": {
            "protein_2": ["output_type_1", "output_type_2"],
            "protein_3": ["output_type_3"],
            "general": ["output_type_4"]
        }
    }
}
</QueryParser>

Now, let's start.

User's request: PUT_USER_REQUEST_HERE
"""


class QueryParser(BaseAPI):
    """
    A sub-agent that selects a tool for the user's request.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def stream_chat(self, request: str):
        """
        Stream chat with the user
        """
        
        try:
            
            input_tool_arg_desc = ""
            for tool, desc in INPUT_FLOW_ARG_DESCRIPTION.items():
                input_tool_arg_desc += f"- {tool}: {desc}\n"
            
            for tool, desc in CONFIGURATIVE_ARG_DESCRIPTION.items():
                input_tool_arg_desc += f"- {tool}: {desc}\n"
                
            output_tool_arg_desc = ""
            for tool, desc in OUTPUT_FLOW_ARG_DESCRIPTION.items():
                output_tool_arg_desc += f"- {tool}: {desc}\n"
            
            for tool, desc in TOOL_SPECIFIC_ARG_DESCRIPTION.items():
                output_tool_arg_desc += f"- {tool}: {desc}\n"
            
            # Identify the input types
            prev_response_list = []
            max_retry_times = 3
            for _ in range(max_retry_times):
                prev_response = "\n".join(prev_response_list)
                
                # Generate system prompt
                system_prompt = SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", request)
                system_prompt = system_prompt.replace("PUT_INPUT_TOOL_ARG_DESCRIPTION_HERE", input_tool_arg_desc)
                system_prompt = system_prompt.replace("PUT_OUTPUT_TOOL_ARG_DESCRIPTION_HERE", output_tool_arg_desc)
                system_prompt = system_prompt.replace("PUT_PREVIOUS_RESPONSES_HERE", prev_response)
                
                input_messages = [{"role": "user", "content": system_prompt}]
                response = self.client.call_openai(
                    messages=input_messages,
                    stream=True,
                    temperature=0.001,
                )
                
                # Get the response
                complete = ""
                for chunk in response:
                    content = "" if chunk.choices[0].delta is None else chunk.choices[0].delta.content or ""
                    complete += content
                    yield AgentResponse(
                        content=complete,
                        status=AGENT_STATUS.GENERATING
                    )


                dict_str = complete.split("<QueryParser>")[-1].split("</QueryParser>")[0]

                try:
                    complete_dict = json_repair.loads(dict_str)
                    input_dict = complete_dict["content"]["input"]
                except Exception as e:
                    error_msg = {
                        "sender": "query_parser",
                        "content": {
                            "error": f"Failed to extract the inputs. {e}"
                        }
                    }
                    yield AgentResponse(
                        content=json.dumps(error_msg, indent=4),
                        status=AGENT_STATUS.GENERATING
                    )
                    continue
                    
                prev_response_list.append(json.dumps(input_dict, indent=4))
                # Verify the input types
                true_dict = {}
                wrong_dict = {}
                
                for entity, type_dict in input_dict.items():
                    wrong_dict[entity] = {}
                    true_dict[entity] = {}
                    for input_type, values in type_dict.items():
                        # If the input type is valid
                        if input_type not in INPUT_FLOW_ARG_DESCRIPTION and input_type not in CONFIGURATIVE_ARG_DESCRIPTION:
                            wrong_dict[entity][input_type] = values
                        
                        elif len(values) == 0:
                            # wrong_dict[input_type] = values
                            pass
                        
                        else:
                            for value in values:
                                # If the value is not valid
                                if type_check("None", value, input_type, self.tool_manager.out_dir) is not None:
                                    wrong_dict[entity][input_type] = wrong_dict[entity].get(input_type, []) + [value]
                                
                                else:
                                    true_dict[entity][input_type] = true_dict[entity].get(input_type, []) + [value]
                    if wrong_dict[entity] == {}:
                        del wrong_dict[entity]
                    if true_dict[entity] == {}:
                        del true_dict[entity]

                # If there are invalid identifications, add them to the previous response and regenerate the response
                if wrong_dict:
                    verify_dict = {
                        "correct_identification": true_dict,
                        "wrong_identification": wrong_dict
                    }
                    prev_response_list.append(json.dumps(verify_dict, indent=4))

                else:
                    complete_dict["content"]["input"] = true_dict
                    yield AgentResponse(
                        content=json.dumps(complete_dict, indent=4),
                        status=AGENT_STATUS.GENERATING
                    )
                    break
            
            if wrong_dict:
                error_msg = {
                    "sender": "query_parser",
                    "analysis": "Take care of these wrong identification, they might have some formatting issues. Remember to notify the user in the final response.", 
                    "content": {
                        "error": "Failed to extract some inputs.",
                        "correct_identification": true_dict,
                        "wrong_identification": wrong_dict
                    }
                }
                yield AgentResponse(
                    content=json.dumps(error_msg, indent=4),
                    status=AGENT_STATUS.GENERATING
                )
                
        except Exception as e:
            error_msg = {
                "sender": "query_parser",
                "analysis": f"An error occurred while parsing the request: {str(e)}",
            }
            yield AgentResponse(
                content=json.dumps(error_msg, indent=4),
                status=AGENT_STATUS.ERROR
            )