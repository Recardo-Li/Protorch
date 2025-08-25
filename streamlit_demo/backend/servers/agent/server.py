import os

import torch
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import signal
import sys


root_dir = __file__.rsplit("/", 5)[0]
if root_dir not in sys.path:
    sys.path.append(root_dir)

import uvicorn
import os
import argparse
import json
import asyncio
import time

from init_agent import prot_agent
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from streamlit_demo.backend.server_tool import check_port_in_use, get_ip
from agent.utils.constants import AGENT_STATUS


app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
os.makedirs(f"{BASE_DIR}/cache", exist_ok=True)
os.makedirs(f"{BASE_DIR}/server_list", exist_ok=True)

# Flag to indicate whether the user has confirmed the tool call
user_confirmation = False


def signal_handler(sig, frame):
    print("\nShutting down gracefully...")
    # 执行清理操作，如终止工具和进程
    for tool in prot_agent.tool_manager.tools.values():
        tool.terminate()
    
    sys.exit(0)
    
     # 终止Uvicorn服务器
    server.should_exit = True
    
    # 等待所有子进程退出
    while server.workers:
        os.waitpid(next(iter(server.workers.keys())), 0)
    
    print("All workers have been terminated.")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


async def generate_response(messages: list[dict]):
    """
    Args:
        messages: Each message is a dictionary with the following keys:
            - role: The role of the speaker. Should be one of ["user", "assistant"].
            - content: The content of the message.
    """
    try:
        # Set server state to busy
        set_state("busy")
        global user_confirmation
        user_confirmation = False
        
        user_request = messages[-1]["content"]
        stream_output = prot_agent.stream_chat(user_request)
        for agent_response in stream_output:
            if get_state() == "stop":
                terminate()
                break
            
            ip_port = f"{get_ip()}:{PORT}"
            d = agent_response.to_dict()
            # Add ip_port to the response for later use
            d.ip_port = ip_port
            yield json.dumps(d)
            
            # If the agent is calling a tool, wait for the user to modify the tool call
            if agent_response.status == AGENT_STATUS.TOOL_CALLING and agent_response.tool_arg["name"] != "chat":
                while True:
                    if user_confirmation:
                        user_confirmation = False
                        break
                    await asyncio.sleep(1)
        
    except Exception as e:
        # raise e
        yield json.dumps({"error": str(e)})
    
    finally:
        # Set server state to idle
        set_state("idle")
        

@app.get("/chat")
async def chat(out_dir: str, messages: str):
    """
    This function is used to chat with the agent
    Args:
        out_dir: Directory to save all output files
        
        messages: Each message is a dictionary with the following keys:
            - role: The role of the speaker. Should be one of ["user", "assistant"].
            - content: The content of the message.
    """
    # Set the output directory
    prot_agent.tool_manager.set_out_dir(out_dir)
    messages = json.loads(messages)
    return StreamingResponse(generate_response(messages), media_type="text/plain")


@app.get("/change_tool_call")
def change_tool_call(tool_name: str, tool_args: str):
    """
    Change the tool call
    Args:
         tool_name: Changed tool name
         tool_args: Changed tool arguments
    """
    try:
        tool_args = json.loads(tool_args)
        prot_agent.tool_executor.change_tool_call(tool_name, tool_args)
        
        # Set user confirmation flag
        global user_confirmation
        user_confirmation = True
        return_dict = {"status": "Success"}
    
    except Exception as e:
        # raise e
        return_dict = {"error": str(e)}
    
    finally:
        return return_dict


@app.get("/sync_toolset")
def sync_toolset(out_dir: str):
    """
    Sync the toolset
    """
    try:
        prot_agent.sync_tool_manager()
        prot_agent.tool_manager.set_out_dir(out_dir)
        prot_agent.tool_manager.initialize_retriever()
        return_dict = {"status": "Success",
                       "detail": list(prot_agent.tool_manager.tools.keys())}
        # return_dict = {"status": "Success"}
    
    except Exception as e:
        return_dict = {"error": str(e)}
    
    finally:
        return return_dict


def terminate():
    """
    Terminate the generation process
    """
    try:
        global user_confirmation
        user_confirmation = True
        
        # Terminate the tool
        for tool in prot_agent.tool_manager.tools.values():
            tool.terminate()
        
        return_dict = {"status": "Success"}
    
    except Exception as e:
        return_dict = {"error": str(e)}
    
    finally:
        return return_dict
    

# Set server state
def set_state(state: str):
    flag_path = f"{BASE_DIR}/server_list/{get_ip()}:{PORT}.flag"
    with open(flag_path, "w") as w:
        w.write(state)


def get_state():
    flag_path = f"{BASE_DIR}/server_list/{get_ip()}:{PORT}.flag"
    with open(flag_path, "r") as r:
        return r.read().strip()
    

# Specify the server port
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=None)
args = parser.parse_args()

if args.port is None:
    PORT = 7862
    while check_port_in_use(PORT):
        PORT += 1

else:
    PORT = args.port
    

def run_server():
    # Generate IP flag
    set_state("idle")
    config = uvicorn.Config(app=app, host="0.0.0.0", port=PORT)
    server = uvicorn.Server(config=config)
    server.run()


if __name__ == "__main__":
    run_server()
