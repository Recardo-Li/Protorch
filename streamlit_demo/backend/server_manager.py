import sys

ROOT_DIR = __file__.rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import uvicorn
import os
import requests
import json
import time

from server_tool import get_ip, check_port
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from easydict import EasyDict


app = FastAPI()
BACKEND_DIR = os.path.dirname(__file__)

# Map the function name to the server directory
FUNCTION_MAP = {
    "chat": f"{BACKEND_DIR}/servers/agent/server_list",
}


def set_state(function: str, ip: str, state: str):
    flag_path = f"{FUNCTION_MAP[function]}/{ip}.flag"
    with open(flag_path, "w") as w:
        w.write(state)


def get_idle_node(server_dir: str) -> str:
    """
    Find an idle node in the server list to perform the request
    
    Returns:
        ip_port: IP address of the idle node
    """

    # Find the first idle node
    server_list = list(filter(lambda x: x.endswith(".flag"), os.listdir(server_dir)))
    # Sort by the last modified time
    server_list.sort(key=lambda file: os.path.getmtime(f"{server_dir}/{file}"))
    
    for ip_port in server_list:
        ip, port = ip_port.split(".flag")[0].split(":")
        ip_info = f"{server_dir}/{ip_port}"

        # Remove inaccessible server
        if not check_port(ip, int(port)):
            os.remove(ip_info)
            continue

        with open(ip_info, "r") as r:
            state = r.read()

        if state == "idle":
            return ip_port.split(".flag")[0]
    
    # No idle node
    raise Exception("No idle node available")
    

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
    try:
        ip = get_idle_node(FUNCTION_MAP["chat"])
        
        def yield_response():
            #  Return the IP address of the idle node
            yield json.dumps({"ip_port": str(ip)})
            
            # Send request to the idle node
            url = f"http://{ip}/chat"
            params = {
                "out_dir": out_dir,
                "messages": messages,
            }
            response = requests.get(url=url, params=params, stream=True)
            yield from response.iter_content(chunk_size=50)
            
        return StreamingResponse(yield_response(), media_type="text/plain")
    
    except Exception as e:
        def yield_err(err):
            yield json.dumps({"error": str(err)})
        
        return StreamingResponse(yield_err(e), media_type="text/plain")


@app.get("/change_tool_call")
def change_tool_call(ip: str, tool_name: str, tool_args: str):
    """
    Change the tool call at given agent node
    Args:
        ip: IP address of the node
        
        tool_name: Changed tool name
        
        tool_args: Changed tool arguments
    """
    # Send request to the idle node
    url = f"http://{ip}/change_tool_call"
    params = {
        "tool_name": tool_name,
        "tool_args": tool_args,
    }
    
    response = requests.get(url=url, params=params).json()
    return response


@app.get("/sync_toolset")
def sync_toolset(out_dir: str):
    """
    Sync the toolset
    Args:
        out_dir: Directory to save all output files
    """
    try:
        ip = get_idle_node(FUNCTION_MAP["chat"])
        
        # Send request to the idle node
        url = f"http://{ip}/sync_toolset"
        params = {
            "out_dir": out_dir,
        }
        
        response = requests.get(url=url, params=params).json()
        return response
    
    except Exception as e:
        return {"error": str(e)}
    
    
@app.get("/terminate")
def terminate(ip: str):
    """
    Terminate the generation process at given agent node
    Args:
        ip: IP address of the node
        
        tool_name: Tool name to terminate
    """
    
    # Change the state of the server to stop chatting
    set_state("chat", ip, "stop")


PORT = 7861


if __name__ == "__main__":
    uvicorn.run("server_manager:app", host="0.0.0.0", port=PORT)
