import sys
import os
import json
import time
import json_repair

ROOT_DIR = __file__.rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.utils.constants import AGENT_STATUS, AgentResponse
from agent.agent.utils import *
from agent.tools.tool_manager import ToolManager
from agent.workflow.workflow_manager import WorkflowManager
from agent.agent.subagents import (
    QueryParser,
    PlanGenerator,
    ToolConnector,
    ToolExecutor,
    Responder,
    Titler
)


class MultiAgentBackbone:
    def __init__(self,
                 model_name: str,
                 tool_manager: ToolManager,
                 max_plan_turn: int = 5,
                 max_step_turn: int = 2):
        """
        Args:
            model_name: The name of the api model
            tool_manager: The tool manager object.
        """
        self.tool_manager = tool_manager
        self.workflow_manager = WorkflowManager(tool_manager=tool_manager)
        
        self.query_parser = QueryParser(model_name=model_name, tool_manager=tool_manager)
        self.plan_generator = PlanGenerator(model_name=model_name, tool_manager=tool_manager)
        self.tool_connector = ToolConnector(model_name=model_name, tool_manager=tool_manager)
        self.tool_executor = ToolExecutor(model_name=model_name, tool_manager=tool_manager)
        self.responder = Responder(model_name="gemini-2.5-pro", tool_manager=tool_manager)
        self.titler = Titler(model_name="gemini-2.5-pro", tool_manager=tool_manager)
        self.max_plan_turn = max_plan_turn
        self.max_step_turn = max_step_turn
    
    def stream_chat(self, request: str, skip_workflow: bool = False, skip_namer: bool = False):
        """
        Stream chat with the user
        Args:
            request: The user request.
        """
        
        now = time.time()
        
        # Store all messages
        message_pool = []
        # Maximum number of turns for plan generation
        max_plan_turn = self.max_plan_turn
        # Maximum number of turns for each step
        max_step_turn = self.max_step_turn
        
        try:
            message_pool.append("")
            for response in self.query_parser.stream_chat(request):
                message_pool[-1] = response.content
                yield AgentResponse(
                    content=json.dumps(message_pool),
                    # workflow=json.dumps(self.workflow_manager.workflow2json()),
                    status=AGENT_STATUS.GENERATING,
                )
            
            query_parser_output = json_repair.loads(message_pool[-1])
            message_pool[-1] = query_parser_output
            
            # self.workflow_manager.set_query_io(query_parser_output["content"])
            yield AgentResponse(
                content=json.dumps(message_pool),
                # workflow=json.dumps(self.workflow_manager.workflow2json()),
                status=AGENT_STATUS.GENERATING,
            )
            
            new_time = time.time()
            print(f"Query parsing took {new_time - now:.2f} seconds")
            now = new_time
            
            plan = None
            for _ in range(max_plan_turn):
                
                if plan is None:
                    message_pool.append("")
                    for response in self.plan_generator.stream_chat(request, message_pool[:-1]):
                        message_pool[-1] = response.content
                        yield AgentResponse(
                            content=json.dumps(message_pool),
                            # workflow=json.dumps(self.workflow_manager.workflow2json()),
                            status=AGENT_STATUS.GENERATING,
                        )
                        
                    plan_generator_output = json_repair.loads(message_pool[-1])
                    message_pool[-1] = plan_generator_output
                    
                    plan = json_repair.loads(plan_generator_output["content"]) if not isinstance(plan_generator_output["content"], dict) else plan_generator_output["content"]
                    
                    plan = {k: v for k, v in plan.items() if k.startswith("step_")}
                    # self.workflow_manager.set_workflow(plan_generator_output["content"])
                    yield AgentResponse(
                        content=json.dumps(message_pool),
                        # workflow=json.dumps(self.workflow_manager.workflow2json()),
                        status=AGENT_STATUS.GENERATING,
                    )
                    
                    new_time = time.time()
                    print(f"Plan generation took {new_time - now:.2f} seconds")
                    now = new_time
                    
                # Assume the task is complete. If any step is not complete, set it to False later.
                task_complete = True
                step_complete = True
                # Execute the plan
                for i in range(len(plan)):
                    # task_complete is False means the execution failed
                    if not task_complete:
                        break
                    
                    step_id = f"step_{i + 1}"
                    
                    
                    if plan[step_id].get('executed','').lower() == "yes" or plan[step_id].get('status', '').lower() == "executed":
                        # self.workflow_manager.current_step = step_id
                        continue
                    
                    message_pool.append("")
                    for response in self.tool_connector.stream_chat(user_request=request, plan=plan, step_id=step_id, message_pool=message_pool[:-1]):
                        message_pool[-1] = response.content
                        yield AgentResponse(
                            content=json.dumps(message_pool),
                            # workflow=json.dumps(self.workflow_manager.workflow2json()),
                            status=AGENT_STATUS.GENERATING,
                        )
                    connector_output = json_repair.loads(message_pool[-1])
                    message_pool[-1] = connector_output
                    
                    if "error" in connector_output["content"]:
                        pass
                        # step_complete = False
                        # plan = None
                        # break
                    
                    
                        # try:
                        #     self.workflow_manager.insert_tool_chain(connector_output["content"])
                        #     plan = self.workflow_manager.workflow2json()
                        #     connector_msg = {
                        #         "sender": "planner", 
                        #         "analysis": "Inserted a tool chain to connect the tools.",
                        #         "content": json.dumps(plan)
                        #     }
                        #     message_pool.append(connector_msg)
                        #     yield AgentResponse(
                        #         content=json.dumps(message_pool),
                        #         status=AGENT_STATUS.GENERATING,
                        #     )
                        #     yield AgentResponse(
                        #         content="",
                        #         workflow=json.dumps(self.workflow_manager.workflow2json()),
                        #         status=AGENT_STATUS.WORKFLOW,
                        #     )
                        # except Exception as e:
                        #     connector_msg ={
                        #         "sender": "tool_connector",
                        #         "analysis": f"Tried all possible tool chains but failed to connect the tools. {e}",
                        #         "content": connector_output["content"]
                        #     }
                        #     message_pool[-1] = connector_msg
                        #     yield AgentResponse(
                        #         content=json.dumps(message_pool),
                        #         status=AGENT_STATUS.GENERATING,
                        #     )
                        #     plan = None
                        
                    # else:
                        # self.workflow_manager.connect_tool_node(connector_output["content"])
                        # yield AgentResponse(
                        #     content=json.dumps(message_pool),
                        #     workflow=json.dumps(self.workflow_manager.workflow2json()),
                        #     status=AGENT_STATUS.GENERATING,
                        # )
                    
                    new_time = time.time()
                    print(f"Tool connector took {new_time - now:.2f} seconds")
                    now = new_time
                    
                    message_pool.append("")
                    for response in self.tool_executor.stream_chat(plan=plan, step_id=step_id, message_pool=message_pool[:-1]):
                        message_pool[-1] = response.content
                        yield AgentResponse(
                            content=json.dumps(message_pool),
                            # workflow=json.dumps(self.workflow_manager.workflow2json()),
                            status=AGENT_STATUS.GENERATING,
                        )
                    
                    tool_executor_output = json_repair.loads(message_pool[-1])
                    message_pool[-1] = tool_executor_output
                    
                    status = tool_executor_output["content"].get("status", "error")
                    if status == "error":
                        step_complete = False
                        plan = None
                        break
                    elif status == "success":
                        # self.workflow_manager.execute_toolnode(tool_executor_output["content"])
                        step_complete = True
                        yield AgentResponse(
                            content=json.dumps(message_pool),
                            # workflow=json.dumps(self.workflow_manager.workflow2json()),
                            status=AGENT_STATUS.GENERATING,
                        )
                    else:
                        raise ValueError(f"Unknown tool_executor status: {status}")

                    new_time = time.time()
                    print(f"Tool executor took {new_time - now:.2f} seconds")
                    now = new_time
                    
                # Go back and revise the plan
                if not step_complete:
                    task_complete = False
                    continue
                
                # Break the plan turn loop when the task is complete
                if task_complete:
                    break
            
            # Generate the final response
            message_pool.append("")
            for response in self.responder.stream_chat(request, message_pool):
                message_pool[-1] = response.content
                yield AgentResponse(
                    content=json.dumps(message_pool),
                    status=AGENT_STATUS.FINAL_RESPONSE,
                )
            
            new_time = time.time()
            print(f"Responder took {new_time - now:.2f} seconds")
            now = new_time
            
            final_response = json_repair.loads(message_pool[-1])
            final_response["task_complete"] = task_complete
            message_pool[-1] = final_response
            
            if not skip_workflow:
                yield AgentResponse(
                    content=json.dumps(message_pool),
                    status=AGENT_STATUS.WORKFLOW,
                )
                try:
                    final_workflow = self.message2workflow(message_pool)
                    
                    # print(final_workflow)
                    
                except Exception as e:
                    print(f"Error in message2workflow: {e}")
                    final_workflow = {}
                
                new_time = time.time()
                print(f"Workflow generation took {new_time - now:.2f} seconds")
                now = new_time
            
            else:
                final_workflow = {}
            
            if not skip_namer:
                # print(final_workflow)
                # Generate a chat title
                message_pool.append("")
                for response in self.titler.stream_chat(request, final_response["content"]):
                    message_pool[-1] = response.content
                    yield AgentResponse(
                        content=json.dumps(message_pool),
                        workflow=json.dumps(final_workflow),
                        status=AGENT_STATUS.TITLE,
                    )

                title = json_repair.loads(message_pool[-1])
                message_pool[-1] = title
                
                new_time = time.time()
                print(f"Title generation took {new_time - now:.2f} seconds")
                now = new_time
            
            # Reset the agent state
            yield AgentResponse(
                content=json.dumps(message_pool),
                workflow=json.dumps(final_workflow),
                status=AGENT_STATUS.IDLE
            )
        except Exception as e:
            # print(e)
            # raise
            yield AgentResponse(
                content=json.dumps(message_pool),
                workflow=json.dumps(self.workflow_manager.workflow2json()),
                status=AGENT_STATUS.ERROR,
                error=str(e)
            )
    
    
    def message2workflow(self, message_pool):
        """
        Convert a message pool to a workflow.
        Args:
            message_pool: A list of messages, each message is a dictionary.
        Returns:
            A Workflow object.
        """
        plan = None
        execution_info = []
        connection_info = []
        for msg in message_pool:
            if isinstance(msg, str):
                msg = json_repair.loads(msg)
            if isinstance(msg, dict):
                sender = msg.get("sender")
                content = msg.get("content")
                if sender == "planner":
                    plan = content
                    execution_info = []
                elif sender == "tool_connector":
                    connection_info.append(content)
                elif sender == "tool_executor":
                    execution_info.append(content)

        if plan is None:
            return {}
        
        self.workflow_manager.set_workflow(plan)
        
        try:
            for conn in connection_info:
                self.workflow_manager.connect_tool_node(conn)
        except:
            self.workflow_manager.valid_workflow = False
        
        for exec_info in execution_info:
            self.workflow_manager.execute_toolnode(exec_info)
        
        workflow_dict = self.workflow_manager.workflow2json()
        workflow_dict["valid_workflow"] = self.workflow_manager.valid_workflow
        # print(workflow_dict)
        return workflow_dict


