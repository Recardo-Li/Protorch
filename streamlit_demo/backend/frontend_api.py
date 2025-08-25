"""
This file contains multiple wrapped functions that are called by the frontend to interact with the agent.
"""

import requests
import json

from easydict import EasyDict


def get_agent_response(out_dir: str, messages: list[dict]):
    """
    Get the agent response based on the input messages.
    Args:
        out_dir: Directory to save all output files
        
        messages: Each message is a dictionary with the following keys:
            - role: The role of the speaker. Should be one of ["user", "assistant"].
            - content: The content of the message.
        
        reset: Whether to reset the agent. If False, the agent will continue the previous generation.
    """
    
    # Send search request
    params = {
        "out_dir": out_dir,
        "messages": json.dumps(messages),
    }
    
    url = f"http://127.0.0.1:7861/chat"
    response = requests.get(url=url, params=params, stream=True)
    
    iterator = response.iter_content(chunk_size=50)
    try:
        ip_port = json.loads(next(iterator))["ip_port"]
        yield ip_port
    except:
        raise Exception("Server busy, please wait and try again later...")
    
    dumped_dict = b""
    for i, chunk in enumerate(response.iter_content(chunk_size=50)):
        # Concatenate bytes to form a complete JSON object
        dumped_dict += chunk
        try:
            agent_response = json.loads(dumped_dict)
            yield EasyDict(agent_response)

            # Reset the dumped_dict
            dumped_dict = b""
        
        except Exception as e:
            # The response is not a complete JSON object
            pass


def change_tool_call(ip_port: str, tool_name: str, tool_args: dict):
    """
    Change the tool call
    Args:
        ip_port: IP address of the agent node
        tool_name: Changed tool name
        tool_args: Changed tool arguments
    """
    # Send search request
    params = {
        "ip": ip_port,
        "tool_name": tool_name,
        "tool_args": json.dumps(tool_args)
    }
    
    url = f"http://127.0.0.1:7861/change_tool_call"
    response = requests.get(url=url, params=params).json()
    return response


def sync_toolset(out_dir: str):
    """
    Sync the toolset
    Args:
        out_dir: Directory to save all output files
    """
    # Send search request
    params = {
        "out_dir": out_dir,
    }
    
    url = f"http://127.0.0.1:7861/sync_toolset"
    response = requests.get(url=url, params=params).json()
    return response

def terminate(ip_port: str):
    """
    Terminate the generation process
    Args:
        ip_port: IP address of the agent node
        tool_name: Tool name to terminate
    """
    # Send search request
    params = {
        "ip": ip_port,
    }
    
    url = f"http://127.0.0.1:7861/terminate"
    response = requests.get(url=url, params=params).json()
    return response
