import json
import json_repair
import itertools
import random
import copy
import streamingjson


from typing import List, Dict
from agent.agent.subagents.base_agent import BaseAPI
from agent.utils.constants import AGENT_STATUS, AgentResponse

CONNECT_SYSTEM_PROMPT = """ \
You are an expert AI assistant specializing in data transformation for tool and API chaining. Your primary objective is to transform an output value from a Source Tool to make it a valid input for a Target Tool.

You will be provided with the following information:

1. Source Tool Output:

Parameter Name: PUT_SOURCE_PARAMETER_NAME_HERE
Parameter Value: PUT_SOURCE_PARAMETER_VALUE_HERE
Tool Documentation: 
PUT_SOURCE_TOOL_DOCUMENTATION_HERE

2. Target Tool Input:

Parameter Name: PUT_TARGET_PARAMETER_NAME_HERE
Tool Documentation: 
PUT_TARGET_TOOL_DOCUMENTATION_HERE

When you receive a request, you must follow these rules:
1. Carefully examine the Source Parameter Value and the requirements of the Target Input Parameter based on the provided documentation.
2. If a direct match or a logical conversion is possible, transform the Source Parameter Value into a new value that is valid for the Target Input Parameter.
3. If a valid transformation is not possible (e.g., due to incompatible data types like converting a complex object to a simple string, or missing information), the transformed_value in your output must be empty.
4. In the analysis field, provide a concise, step-by-step explanation of your reasoning for the transformation or the reason for it being impossible.

You should adjust the output parameter in the following format: First generate a "<Connector>" tag, then adjust the output parameter in JSON format, and finally generate a "</Connector>" tag. An example is shown below:

<Connector>
{
    "sender": "connector",
    "content": {
        "source": "value of the output parameter that matches the input parameter",
        "target": "adjusted value of the input parameter or empty if not possible",
        "analysis": "analysis of the output parameter and input parameter to determine the adjusted value"
    }
}
</Connector>

Now, let's start adjusting the output parameter to match the input parameter.
"""

EXTRACT_SYSTEM_PROMPT = """ \
You are an expert AI specializing in parameter extraction for API and tool chaining. Your primary task is to extract a single parameter value from a user's request, conforming to the specifications of a target tool.

You will be provided with the following information:

1. User Request:
PUT_USER_REQUEST_HERE

2. Target Tool Input:
Parameter Name: PUT_TARGET_PARAMETER_NAME_HERE
Tool Documentation:
PUT_TARGET_TOOL_DOCUMENTATION_HERE

When you receive a request, you must follow these rules:
1. Analyze the User Request against the Target Parameter's Documentation.
2. Extract and transform the relevant information to create a valid value for the parameter. This may involve direct extraction, logical inference, or format conversion.
3. If the User Request does not contain a valid value for the Target Input Parameter, the extracted_value in your output MUST be empty.
4. In the analysis field, provide a concise, step-by-step analysis explaining your reasoning. If extraction is not possible, explain why.

You should adjust the output parameter in the following format: First generate a "<Connector>" tag, then adjust the output parameter in JSON format, and finally generate a "</Connector>" tag. An example is shown below:

<Connector>
{
    "sender": "connector",
    "content": {
        "source": "piece of the user request that matches the input parameter",
        "target": "adjusted value of the input parameter or empty if not possible",
        "analysis": "analysis of the output parameter and input parameter to determine the adjusted value"
    }
}
</Connector>

Now, let's start adjusting the output parameter to match the input parameter.
"""

class ToolConnector(BaseAPI):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def connect_tool(self, source_name, source_value, source_doc, target_name, target_doc):
        """
        Connects the output of a source tool to the input of a target tool.
        
        Args:
            source_name (str): The name of the source parameter.
            source_value (Any): The value of the source parameter.
            source_doc (str): The documentation of the source tool.
            target_name (str): The name of the target parameter.
            target_doc (str): The documentation of the target tool.
        
        Returns:
            AgentResponse: The response containing the transformed value or null if not possible.
        """
        system_prompt = CONNECT_SYSTEM_PROMPT.replace("PUT_SOURCE_PARAMETER_NAME_HERE", source_name) \
                        .replace("PUT_SOURCE_PARAMETER_VALUE_HERE", str(source_value)) \
                        .replace("PUT_SOURCE_TOOL_DOCUMENTATION_HERE", source_doc) \
                        .replace("PUT_TARGET_PARAMETER_NAME_HERE", target_name) \
                        .replace("PUT_TARGET_TOOL_DOCUMENTATION_HERE", target_doc)

        input_messages = [{"role": "user", "content": system_prompt}]
        response = self.client.call_openai(
            messages=input_messages,
            stream=True,
            temperature=0.001,
        )
        
        complete = ""
        for chunk in response:
            content = (
                    ""
                    if chunk.choices[0].delta is None
                    else chunk.choices[0].delta.content or ""
                )
            complete += content
        
        connection_str = complete.split("<Connector>")[-1].split("</Connector>")[0]
        connection = json_repair.loads(connection_str)
        return connection

    def extract_parameter(self, user_request: str, target_name: str, target_doc: str):
        """
        Extracts a parameter from the user request based on the target tool's documentation.
        
        Args:
            user_request (str): The user's request containing the parameter to be extracted.
            target_name (str): The name of the target parameter to be extracted.
            target_doc (str): The documentation of the target tool.
        
        Returns:
            AgentResponse: The response containing the extracted value or null if not possible.
        """
        system_prompt = EXTRACT_SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", user_request) \
                        .replace("PUT_TARGET_PARAMETER_NAME_HERE", target_name) \
                        .replace("PUT_TARGET_TOOL_DOCUMENTATION_HERE", target_doc)

        input_messages = [{"role": "user", "content": system_prompt}]
        response = self.client.call_openai(
            messages=input_messages,
            stream=True,
            temperature=0.001,
        )
        
        complete = ""
        for chunk in response:
            content = (
                    ""
                    if chunk.choices[0].delta is None
                    else chunk.choices[0].delta.content or ""
                )
            complete += content
        
        extraction_str = complete.split("<Connector>")[-1].split("</Connector>")[0]
        extraction = json_repair.loads(extraction_str)
        return extraction

    def stream_chat(self, user_request: str, plan: dict, step_id: str, message_pool: List[Dict]):
        """
        Stream chat with the user
        Args:
            plan: The plan dictionary.
            step_id: Current task ID.
            message_pool: The pool of messages generated by other agents.
        """
        
        try:
            tool_name = plan[step_id]["tool"]
            tool_description = self.tool_manager.generate_document([tool_name])
            input_args = self.tool_manager.generate_argument_document(tool_name)
            input_args = json_repair.loads(input_args)
            
            arguments_pool = []
            
            # Collect all available parameters and their values from previous messages
            for msg in message_pool:
                if isinstance(msg, str) and msg.strip() == "":
                    continue
                if not isinstance(msg, dict):
                    msg = json_repair.loads(msg)
                if msg.get("sender", None) == "query_parser":
                    query_parser_msg = msg["content"]
                    if isinstance(query_parser_msg, str):
                        query_parser_msg = json_repair.loads(query_parser_msg)
                    
                    input_extractions = query_parser_msg.get("input", {})
                    if isinstance(input_extractions, str):
                        input_extractions = json_repair.loads(input_extractions)
                    
                    for entity, type_dict in input_extractions.items():
                        for type, value in type_dict.items():
                            available_parameters = {
                                "source": "user_input",
                                "source_id": "input",
                                "name": "user_input",
                                "detailed_type": type,
                                "value": value
                            }
                            arguments_pool.append(available_parameters)
                if msg.get("sender", None) == "tool_executor":
                    tool = msg["content"]["tool_name"]
                    executed_step_id = msg["content"]["current_step"]
                    arg_doc = self.tool_manager.get_tool(tool).config["document"]
                    for name, value in msg["content"].get("results", {}).items():
                        # update parameter name to detailed type
                        for arg in arg_doc["return_values"]:
                            if arg["name"] == name:
                                detailed_type = arg["detailed_type"]
                                available_parameters = {
                                    "source": tool,
                                    "source_id": executed_step_id,
                                    "name": name,
                                    "detailed_type": detailed_type,
                                    "value": value
                                }
                                arguments_pool.append(available_parameters)
                                break
            
            ret_msg = {
                "sender": "tool_connector",
                "analysis": f"Extracted {len(arguments_pool)} useful parameters from previous messages.",
            }
            
            yield AgentResponse(
                status=AGENT_STATUS.GENERATING,
                content=json.dumps(ret_msg, indent=4)
            )
            
            # Make connection plan
            connection_plan = {}
            missing_types = []
            for arg in input_args["required_parameters"]:
                if arg["detailed_type"] not in [param["detailed_type"] for param in arguments_pool]:
                    # No source parameter with the same detailed type
                    # retry extracting the parameter from user input
                    
                    ret_msg = {
                        "sender": "tool_connector",
                        "analysis": f"Trying to extract {arg['detailed_type']} from user input.",
                    }
                    yield AgentResponse(
                        status=AGENT_STATUS.GENERATING,
                        content=json.dumps(ret_msg, indent=4)
                    )
                    
                    target_name = arg["name"]
                    target_doc = tool_description
                    
                    connection_msg = self.extract_parameter(user_request, target_name, target_doc)
                    connection = connection_msg["content"]
                    if connection.get("target"):
                        arg_plan = {
                            "source": "user_input",
                            "source_parameter": "user_input",
                            "source_value": connection["source"],
                            "target_value": connection["target"],
                        }
                        connection_plan[target_name] = arg_plan
                        ret_msg = {
                            "sender": "tool_connector",
                            "analysis": f"Extracted {arg['detailed_type']} from user input.",
                        }
                        
                        yield AgentResponse(
                            status=AGENT_STATUS.GENERATING,
                            content=json.dumps(ret_msg, indent=4)
                        )
                        
                    else:                    
                        missing_types.append(arg["detailed_type"])
                else:
                    for param in arguments_pool:
                        if param["detailed_type"] == arg["detailed_type"]:
                            source_tool = param["source"]
                            source_name = param["name"]
                            source_value = param["value"]
                            if source_name == "user_input":
                                source_doc = "Skip generation since this parameter comes from user input"
                            else:
                                source_doc = self.tool_manager.generate_document([param["source"]])
                            target_name = arg["name"]
                            target_doc = tool_description
                            
                            ret_msg = {
                                "sender": "tool_connector",
                                "analysis": f"Trying to connect {source_tool} ({source_name}) to {target_name} with value {source_value}.",
                            }
                            yield AgentResponse(
                                status=AGENT_STATUS.GENERATING,
                                content=json.dumps(ret_msg, indent=4)
                            )
                            
                            connection_msg = self.connect_tool(source_name, source_value, source_doc, target_name, target_doc)
                            connection = connection_msg["content"]
                            if connection.get("target"):
                                arg_plan = {
                                    "source": source_tool,
                                    "source_id": param["source_id"],
                                    "source_parameter": source_name,
                                    "source_value": connection["source"],
                                    "target_value": connection["target"],
                                }
                                connection_plan[target_name] = arg_plan
                                
                                ret_msg = {
                                    "sender": "tool_connector",
                                    "analysis": f"Connected {source_tool} ({source_name}) to {target_name} with value {connection['target']}.",
                                }
                                yield AgentResponse(
                                    status=AGENT_STATUS.GENERATING,
                                    content=json.dumps(ret_msg, indent=4)
                                )
                                
                                break
                    if connection_plan.get(arg["name"]) is None:
                        # All parameters with the same detailed type are not valid for the input parameter
                        missing_types.append(arg["detailed_type"])
            
            if len(missing_types) > 0:
                ret_msg = {
                    "sender": "tool_connector",
                    "analysis": f"Take care of {tool_name}'s paramter generation with the following types: {', '.join(missing_types)}.",
                    "content": {
                        "current_step": step_id,
                        "tool_name": tool_name,
                        "error": f"Cannot connect the tool {tool_name}.",
                        "arguments_pool": arguments_pool,
                        "missing_types": missing_types,
                    }
                }
            else:
                ret_msg = {
                    "sender": "tool_connector",
                    "analysis": f"Successfully connected the tool {tool_name} with all required parameters.",
                    "content": {
                        "current_step": step_id,
                        "tool_name": tool_name,
                        "connection": connection_plan
                    }
                }
            
            yield AgentResponse(
                status=AGENT_STATUS.GENERATING,
                content=json.dumps(ret_msg, indent=4)
            )
        except Exception as e:
            ret_msg = {
                "sender": "tool_connector",
                "analysis": f"Error occurred while connecting tools: {str(e)}",
            }
            yield AgentResponse(
                status=AGENT_STATUS.ERROR,
                content=json.dumps(ret_msg, indent=4)
            )