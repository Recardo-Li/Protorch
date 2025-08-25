import sys
import os
import json

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

@register_tool
class PrintFile(BaseTool):
    # Support file extensions
    SUPPORTED_EXTENSIONS = [
        '.pdb', '.pdbqt', '.ent', '.cif', '.gro',
        '.mrc', '.sdf', '.mol', 'mol2', '.bcif',
        '.fasta', '.a3m', '.aln', '.fa', '.fna',
        '.faa', '.csv', '.tsv', 'json', '.yaml',
        '.yml', '.xml', '.py', '.sh', '.log',
        '.txt', '.md', '.db'
    ]

    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/printfile", **kwargs):
        super().__init__(
            config_path=os.path.join(BASE_DIR, "config.yaml"),
            out_dir=out_dir,
            **kwargs
        )
        if isinstance(self.config.document, list) and self.config.document:
            self.config.document = self.config.document[0]

    def __call__(self, file_path: str)->dict:
        full_path = os.path.join(self.out_dir, file_path)

        # Check if the file exists
        if not os.path.exists(full_path):
            return {"error": f"File not found: {full_path}"}
        
        #Verify extension support
        _, ext = os.path.splitext(full_path.lower())
        if ext not in self.SUPPORTED_EXTENSIONS:
            return {"error": f"Unsupported file extension: '{ext}'"}
        
        python_exec = self.config.get("python", sys.executable)
        cmd = (
            f"{python_exec} "
            f"{os.path.join(BASE_DIR, 'command.py')} --file_path '{full_path}'"
        )

        cmd += f" > {self.log_path} 2>&1"
        os.system(cmd)

        # Read the output log
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {"error": "Log file not found."}
        
        content = "".join(lines)
        if content.startswith("Traceback") or "Error" in content:
            return {"error": content.strip()}
        
        if len(lines) > 10000:
            return {"error": f"File content exceeds 10,000 lines."}

        return {"content": content}

if __name__ == "__main__":
    tool = PrintFile(out_dir = BASE_DIR)
    args = {"file_path": "example/test.txt"}
    for obs in tool.mp_run(**args):
        print(obs)