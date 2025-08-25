def register_tool(cls):
    global registered_tools
    registered_tools[cls.__name__] = cls
    return cls
    

def get_tools():
    return registered_tools


registered_tools = {}
