import os
import subprocess


class ScriptRunner(object):
    def __init__(self, script_path, script_args, result_path, logger, log_path):
        self.script_path = script_path
        self.script_args = script_args
        self.result_path = result_path
        self.logger = logger
        self.log_path = log_path

    def run(self):
        if type(self.script_path) is list:
            for i, path in enumerate(self.script_path):
                cmd = [path] + self.script_args[i]
                cmd = " ".join(cmd)
                try:
                    # 启动子进程并进行实时读取输出
                    with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                        for line in process.stdout:
                            self.logger.info(line.strip())
                        
                        process.wait()
                except Exception as e:
                    self.logger.error(f"Error: {e}")
                    return {"result": None,
                            "logfile": self.log_path
                            }
                    
            return {"result": self.result_path,
                "filedownload": self.result_path,
                "logfile":self.log_path
                }
        else:
            cmd = [self.script_path] + self.script_args
            cmd = " ".join(cmd)
            try:
                # 启动子进程并进行实时读取输出
                with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                    for line in process.stdout:
                        self.logger.info(line.strip())
                    for line in process.stderr:
                        self.logger.error(line.strip())
                    
                    process.wait()
            except Exception as e:
                self.logger.error(f"Error: {e}")
                return {"result": None,
                        "logfile": self.log_path
                        }

            if os.path.exists(self.result_path):
                return {"result": self.result_path,
                    "filedownload": self.result_path,
                    "logfile":self.log_path
                    }
            else:
                self.logger.error(f"Error: Fail to find result file {self.result_path}")
                return {"result": None,
                        "logfile": self.log_path
                        }
        
