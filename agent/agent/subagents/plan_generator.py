import json
import streamingjson

from typing import List, Dict
from agent.utils.constants import AGENT_STATUS, AgentResponse
from agent.agent.subagents.base_agent import BaseAPI


SYSTEM_PROMPT = """ \
You are a helpful plan generator. Your task is to decompose the user's request into a series of steps that can be executed by different tools.

All tools you can call are described here:
===
PUT_TOOL_DESCRIPTION_HERE
===

Previous chat history is here:
===
PUT_PREVIOUS_RESPONSE_HERE
===

You must follow these directives in order.

1. Determine the Plan Type:
First, you must decide whether to generate an Execution Plan or an Analysis Plan.
a. Check for Existing Plan: If a plan exists in the previous conversation history, you must maintain its type. If the previous plan was an Execution Plan, create a new Execution Plan. If it was an Analysis Plan, create a new Analysis Plan.
b. Initial Plan Creation: If no previous plan exists, assess the available tools against the user's request.
i. If suitable tools exist to directly address the request, create an Execution Plan.
ii. If no suitable tools exist, create an Analysis Plan.

2. Adhere to Plan-Specific Rules:

A. If creating an Execution Plan:
- Tool Sequence: The plan must be a logical sequence of tool calls. Each step must be necessary.
- Failure Handling: If the previous plan failed, analyze the root cause. Modify the new plan by adding, removing, or using different tools to avoid repeating the failure.
- Reuse Successful Steps: To improve efficiency, reuse any steps from the previous plan that successfully produced useful results. Mark these steps as "executed": "Yes" and copy their tool_args and results.
- Data Flow Logic: The plan must be designed to ensure a logical flow of data types. The reason field must explain how the chosen sequence of tools respects this flow (e.g., a tool that outputs a structure is followed by a tool that requires a structure as input).
- Protein Entity Verification: When the user's request involves multiple protein entities, each step in the plan must explicitly target the correct protein. The reason for the step should confirm which protein is being operated on.
- Semantic Precision: The plan must accurately reflect the specific semantic details of the user's request. For example, you must differentiate between:
    - backbone structure vs. all-atom structure
    - domain sequence/structure vs. full sequence/structure
The tool calls and their arguments must precisely match the user's intent.

B. If creating an Analysis Plan:
- Composition: An Analysis Plan must consist exclusively of literature_search tool calls.
- Decomposition: Break down the user's complex request into a series of smaller, core questions or concepts.
- Step Generation: Each step in the plan should be a literature_search call designed to answer one of these core questions.
- Query Formulation: For each step, formulate a concise and effective search query (fewer than 5 words) to be used as the value for the keywords argument.

3. Follow General Rules:

Clarification: If the user's request is ambiguous or lacks essential information, your plan's only step must be a call to the chat tool to ask for clarification.
Final Fallback: If all planning attempts fail or the task is impossible, use the chat tool to inform the user.
Terminal Step: The chat tool is always the final step of any plan. No other steps can follow it.

You should generate the plan in the following format: First generate a "<Planner>" tag, then generate the plan in
JSON format, and finally generate a "</Planner>" tag. An example is shown below:

<Planner>
{
    "sender": "planner",
    "content": {
        "user_request": "PUT_USER_REQUEST_HERE",
        "analysis": "analysis of the user's request and previous chat history to determine the new plan.",
        "step_1": {
                "tool": "xxx",
                "reason": "xxx",
                "executed": "No"
            },
        "step_2": {
                "tool": "yyy",
                "reason": "yyy",
                "executed": "Yes",
                "tool_arg": {
                    "arg_1": "value_1",
                    "arg_2": "value_2"
                },
            },
        "step_3": {
                "tool": "zzz",
                "reason": "zzz",
                "executed": "No"
            }
    }
}
</Planner>

Now, let's start planning.

User: PUT_USER_REQUEST_HERE
"""


class PlanGenerator(BaseAPI):
    """
    A sub-agent that generates a new plan based on the user's request and previous chat history.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def stream_chat(self, user_request: str, message_pool: List[Dict]):
        """
        Stream chat with the user
        Args:
            user_request: The user's request.
        """
        try:
            # Get tool description
            all_tools = list(self.tool_manager.tools)
            tool_desc = self.tool_manager.generate_document(all_tools)


            # Get previous plan description
            chat_history = "\n".join(
                [json.dumps(msg_dict, indent=4) for msg_dict in message_pool]
            )

            # Generate system prompt
            system_prompt = SYSTEM_PROMPT.replace(
                "PUT_TOOL_DESCRIPTION_HERE", tool_desc
            )
            system_prompt = system_prompt.replace("PUT_USER_REQUEST_HERE", user_request)
            system_prompt = system_prompt.replace(
                "PUT_PREVIOUS_RESPONSE_HERE", chat_history
            )

            input_messages = [{"role": "user", "content": system_prompt}]
            response = self.client.call_openai(
                messages=input_messages,
                stream=True,
                temperature=1e-3,
            )

            complete = ""
            lexer = streamingjson.Lexer()
            for chunk in response:
                content = (
                    ""
                    if chunk.choices[0].delta is None
                    else chunk.choices[0].delta.content or ""
                )
                lexer.append_string(content)
                complete += content
                yield AgentResponse(
                    content=lexer.complete_json().split("<Planner>")[-1],
                    status=AGENT_STATUS.GENERATING,
                )

            # Return the plan as a dictionary
            plan = complete.split("<Planner>")[-1].split("</Planner>")[0]
            yield AgentResponse(content=plan, status=AGENT_STATUS.SKIP)
        except Exception as e:
            response = {"sender": "plan_optimizer", "content": {"error": str(e)}}
            yield AgentResponse(
                content=json.dumps(response, indent=4), status=AGENT_STATUS.ERROR
            )
