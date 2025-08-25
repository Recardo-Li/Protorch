import os
import time
import json
import torch
import yaml
import multiprocessing as mp
import copy

from easydict import EasyDict
from agent.tools.type_check import type_check
from agent.utils.others import kill_process

# Timeout for the tool running process is set to 30 min
TOOL_TIMEOUT = 18000


class BaseTool:
    def __init__(self,
                 config_path: str,
                 out_dir: str = None,
                 enable_quick_run: bool = False):
        """
        Args:
            config_path: Path to the ".yaml" config file
            out_dir: Directory to save all output files
            enable_quick_run: If True, the tool will run in quick mode if the config file has an example output
        """
        
        self.enable_quick_run = enable_quick_run
        
        # Load the config file
        with open(config_path, 'r', encoding='utf-8') as r:
            self.config = EasyDict(yaml.safe_load(r))
        
        self.out_dir = out_dir
        if self.out_dir is not None:
            os.makedirs(self.out_dir, exist_ok=True)

        # Multi-processing variables
        self.process = None
        self.results = mp.Manager().dict()
        self.mp_log_path = mp.Manager().Value(str, "")
        if type(self.config.document) is not list:
            self.tool_name = self.config.document["tool_name"]
        else:
            self.tool_name = None
    
    def set_out_dir(self, out_dir: str):
        """
        Set the output directory
        """
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def reset_mp_vars(self):
        """
        Reset the multi-processing variables
        """
        self.process = None
        self.results.clear()
        self.mp_log_path.value = ""

    def get_document(self):
        """
        Get the tool description document
        """
        return json.dumps(self.config.document, indent=4)
    
    def get_argument_document(self):
        args = {
            "required_parameters": self.config.document["required_parameters"],
            "optional_parameters": self.config.document["optional_parameters"]
        }
        return json.dumps(args)
        
    # Different tools have different implementations
    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def check_input(self, tool_args) -> dict:
        """
        Check the input of the tool
        Args:
            tool_args: Arguments for the tool
        """
        error_list = []
        tool_args = copy.deepcopy(tool_args)

        # Check required parameters
        for param in self.config.document["required_parameters"]:
            param_name = param["name"]
            detailed_type = param["detailed_type"]

            if param_name not in tool_args:
                error_list.append(f"Missing required parameter: {param_name}")

            elif (error_msg := type_check(param_name, tool_args.pop(param_name), detailed_type, self.out_dir)) is not None:
                error_list.append(error_msg)

        # Check optional parameters
        for param in self.config.document["optional_parameters"]:
            param_name = param["name"]
            detailed_type = param["detailed_type"]

            if param_name in tool_args and \
                    (error_msg := type_check(param_name, tool_args.pop(param_name), detailed_type, self.out_dir)):
                error_list.append(error_msg)

        # Add unknown parameters to the error list
        for param in tool_args.keys():
            error_list.append(f"Unknown parameter: {param}")

        if error_list:
            error_msg = "\n".join(error_list)
            error_dict = {
                "error": error_msg
            }
            with open(self.log_path, "w") as w:
                w.write(error_msg)

            return error_dict

        else:
            return {}

    def run(self, **tool_arg):
        """
        Call the tool and return the output
        Returns:
            obs: The output of the tool
        """
        now = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        self.log_path = f"{self.out_dir}/{self.tool_name}/run-{self.tool_name}-{now}.log"
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.mp_log_path.value = self.log_path
        try:
            # Check input and return error if invalid
            results = self.check_input(tool_arg)

            # If the input is valid, call the tool
            if not results:
                # If quick run is enabled, return the example output
                if self.enable_quick_run and hasattr(self.config, "example_output"):
                    results = self.quick_run()
                else:
                    results = self(**tool_arg)
                
        except Exception as e:
            results = {"error": str(e)}

        self.results.update(results)
        return results
    
    def quick_run(self) -> dict:
        obs = "Successfully finished the tool call\n"
        
        with open(self.log_path, "w") as w:
            w.write(obs)
        
        return self.config.example_output
    
    def get_result(self):
        """
        Get the result of the tool
        """
        return self.results

    def mp_run(self, *args, **kwargs) -> str:
        """
        Call the tool in a multi-processing way
        """
        self.reset_mp_vars()

        start_time = time.time()
        self.process = mp.Process(target=self.run, args=args, kwargs=kwargs)
        self.process.start()

        # Wait for the log file to be created by the child process
        while self.mp_log_path.value == "":
            time.sleep(0.1)
        self.log_path = self.mp_log_path.value
        
        # Constantly read the running log
        while len(self.results) == 0 and self.process is not None:
            # Read the log file
            if os.path.exists(self.log_path):
                with open(self.log_path, "r") as r:
                    log = r.read()
            else:
                log = "No log file"
            
            if time.time() - start_time > TOOL_TIMEOUT:
                # Remove the absolute path from the log
                log = log.replace(self.out_dir + '/', "")

                obs = "Running log: \n" \
                      f"{log}\n\n" \
                      f"Results: \n" \
                      "{{\"error\": \"Timeout\"}}"
                yield obs
                
                os.remove(self.log_path)
                self.reset_mp_vars()
                self.terminate()
                return
            
            obs = "Running log: \n" \
                  f"{log}\n\n"
            yield obs
            time.sleep(1)

        # Read the final log file when the process is done
        if os.path.exists(self.log_path):
            with open(self.log_path, "r") as r:
                log = r.read()
            os.remove(self.log_path)

        else:
            log = "No log file"

        # Remove the absolute path from the log
        log = log.replace(self.out_dir + '/', "")


        obs = "Running log: \n" \
              f"{log}\n\n" \
              f"Results: \n" \
              f"{self.results}"
        yield obs

        
    def terminate(self):
        """
        Terminate the tool running process
        """
        if self.process is not None:
            while self.process.is_alive():
                kill_process(self.process.pid)

            self.reset_mp_vars()
        
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
