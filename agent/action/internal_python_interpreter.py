import io
from contextlib import redirect_stdout
import torch 
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline 
import os

# 
os.environ["HF_HUB_OFFLINE"] = "1"

class InternalPythonInterpreter():
    def __init__(self, config):
        self.model_path = config.agent.interpreter.path
        self.max_new_tokens = config.agent.interpreter.max_new_tokens
        self.return_full_text = config.agent.interpreter.return_full_text
        self.temperature = config.agent.interpreter.temperature
        self.do_sample = config.agent.interpreter.do_sample
        device_index = config.setting.os_environ.CUDA_VISIBLE_DEVICES
        
        # Not using it at the moment as there is not enough memory on a single GPU
        self.device = ["cuda:"+(index).strip() for index in device_index.split(",")]
        
        
    def get_phi_results(self, command: str, chat_action_history: str):
        model = AutoModelForCausalLM.from_pretrained( 
            self.model_path,  
            device_map="auto",  
            torch_dtype="auto",  
            trust_remote_code=True,  
        ) 
        tokenizer = AutoTokenizer.from_pretrained(self.model_path) 

        messages = [ 
            {"role": "system", "content": "You are a useful python helper. \
                Now you need to modify the python code in the COMMAND:$$Possibly incorrect commands$$ based on the history information in CHAT_ACTION_HISTORY:\
                $$user\nUser's qurey<|im_end|>\n<|im_start|>\
                assistant\nThought 1:\n**The thought generate by LLM**\n\
                Action 1:\n```\naction: a class name which the LLM what to use \n\
                action_input: {'command': 'The command generate by LLM'}\n```\n\
                Observation 1:\n```\n\'dict\' The result after run the command \'format_result\'\n```\n\
                Thought 2:...\n$$, \
                remember not to make changes to the code except for possible runtime errors. Keep in mind that everything you output must be able to be run directly in the python interpreter without any explanatory content, and if there is any, comment that content with #!!!!!!!!"}, 
            {"role": "user", "content": "COMMAND: $$print(1+1)$$, CHAT_ACTION_HISTORY: $$user\nPlease use pythoninterpreter to compute the sum of 1+2.<|im_end|>\n$$"}, 
            {"role": "assistant", "content": "print(1+2)"}, 
            {"role": "user", "content": f"COMMAND: $${command}$$, CHAT_ACTION_HISTORY: $${chat_action_history}$$"}, 
        ] 

        pipe = pipeline( 
            "text-generation", 
            model=model, 
            tokenizer=tokenizer, 
        ) 
        generation_args = { 
            "max_new_tokens": self.max_new_tokens, 
            "return_full_text": self.return_full_text, 
            "temperature": self.temperature, 
            "do_sample": self.do_sample, 
        } 
        output = pipe(messages, **generation_args) 
        return output[0]['generated_text']
    
    def internal_python_interpreter(self, command: str, chat_action_history: str):
        # A string stream to capture the outputs of exec
        output = io.StringIO()
    
        phi_command = self.get_phi_results(command, chat_action_history).strip()  
        try:
            # Redirect stdout to the StringIO object
            with redirect_stdout(output):
                # Allow imports
                exec(phi_command, globals())

        except Exception as e:
            # If an error occurs, capture it as part of the output
            print(f"Error: {e}", file=output)

        # Close the StringIO object and return the output
        value = output.getvalue()
        output.close()
        return {"output": value}



    
