import json

from agent.utils.constants import AGENT_STATUS, AgentResponse, INPUT_TOOL_ARG_DESCRIPTION
from agent.agent.sujin_multi_agent_api.base_agent import BaseAPI
from agent.tools.type_check import type_check


SYSTEM_PROMPT = """ \
You are helpful query parser. Your task is to identify the input types from the user's request. The input types are used
to call the tools.

All available input types are listed below:
===
PUT_TOOL_ARG_DESCRIPTION_HERE
===

Your previously responses are listed below:
===
PUT_PREVIOUS_RESPONSES_HERE
===

When you identify the input types, you must obey these rules:
1. In your previous response, you must keep the correct identification and remove the wrong identification.

When you generate response, you must follow this format:
<QueryParser>
{
    "type_A": ["aaa"],
    "type_B": ["bbb", "ccc"],
    ...
}
</QueryParser>

Now, let's start.

User's request: PUT_USER_REQUEST_HERE
"""


class QueryParserAPI(BaseAPI):
    """
    A sub-agent that selects a tool for the user's request.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def stream_chat(self, request: str):
        """
        Stream chat with the user
        """
        tool_arg_desc = ""
        for tool, desc in INPUT_TOOL_ARG_DESCRIPTION.items():
            tool_arg_desc += f"- {tool}: {desc}\n"
        
        # Identify the input types
        prev_response_list = []
        while True:
            prev_response = "\n".join(prev_response_list)
            
            # Generate system prompt
            system_prompt = SYSTEM_PROMPT.replace("PUT_USER_REQUEST_HERE", request)
            system_prompt = system_prompt.replace("PUT_TOOL_ARG_DESCRIPTION_HERE", tool_arg_desc)
            system_prompt = system_prompt.replace("PUT_PREVIOUS_RESPONSES_HERE", prev_response)
            
            input_messages = [{"role": "user", "content": system_prompt}]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=input_messages,
                stream=True,
                temperature=0.0,
            )
            
            # Get the response
            complete = ""
            for chunk in response:
                complete += chunk.choices[0].delta.content
                yield AgentResponse(
                    content=complete,
                    status=AGENT_STATUS.GENERATING
                )
            
            dict_str = complete.split("<QueryParser>")[-1].split("</QueryParser>")[0]
            type_dict = json.loads(dict_str)
            # Verify the input types
            true_dict = {}
            wrong_dict = {}
            for input_type, values in type_dict.items():
                # If the input type is valid
                if input_type not in INPUT_TOOL_ARG_DESCRIPTION:
                    wrong_dict[input_type] = values
                
                elif len(values) == 0:
                    wrong_dict[input_type] = values
                
                else:
                    for value in values:
                        # If the value is not valid
                        if type_check("None", value, input_type, self.tool_manager.out_dir) is not None:
                            wrong_dict[input_type] = wrong_dict.get(input_type, []) + [value]
                        
                        else:
                            true_dict[input_type] = true_dict.get(input_type, []) + [value]
            
            # If there are invalid identifications, add them to the previous response and regenerate the response
            if wrong_dict:
                verify_dict = {
                    "correct_identification": true_dict,
                    "wrong_identification": wrong_dict
                }
                prev_response_list.append(json.dumps(verify_dict, indent=4))
            
            else:
                yield AgentResponse(
                    content=json.dumps(type_dict, indent=4),
                    status=AGENT_STATUS.GENERATING
                )
                break
                