import shlex
import sys
import time
import json

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import json_repair

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool
from easydict import EasyDict

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class UniprotQuery(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/uniprot_query", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "uniprot_query"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name
        
    def __call__(self, keyword, all_results=False) -> dict:
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{self.out_dir}/uniprot_query/{now}", exist_ok=True)
        json_path = f"{self.out_dir}/uniprot_query/{now}/result.json"
        fasta_path = f"{self.out_dir}/uniprot_query/{now}/result.fasta"
        
        if all_results:
            cmd_args = {
                "query": keyword,
                "save_dir": f"{self.out_dir}/uniprot_query/{now}",
                "all_results": all_results,
            }
        else:
            cmd_args = {
                "query": keyword,
                "save_dir": f"{self.out_dir}/uniprot_query/{now}",
            }
        
        cmd_parts = [f"{self.config['python']} {BASE_DIR}/command.py"]
        for key, value in cmd_args.items():
            cmd_parts.append(f"--{key}")
            # Use shlex.quote() to handle spaces, quotes, and other special characters.
            # It's good practice to cast value to string.
            cmd_parts.append(shlex.quote(str(value)))
        
        cmd_parts.append(f"> {self.log_path} 2>&1")
        cmd = " ".join(cmd_parts)
        
        try:
            os.system(cmd)
            
            if os.path.exists(json_path):
                
                result = {"result_json": json_path[len(self.out_dir)+1:], "fasta_path": fasta_path[len(self.out_dir)+1:]}
                scores = self._extract_fasta(json_path, fasta_path)
                if 'error' in scores:
                    return {'error': scores['error']}
                else:
                    result.update(scores)
                    return result
                
            else:
                return {"error": "Uniprot query did not return any results."}
        except Exception as e:
            # return {"error": str(e)}
            raise

    def _extract_fasta(self, json_path, fasta_path):
        """
        Extracts the FASTA sequence from the JSON file and saves it to the specified path.
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Open the output file
        with open(fasta_path, "w") as fasta_file:
            # Process each result entry
            for entry in data:
                if not isinstance(entry, dict):
                    entry = EasyDict(entry)
                # Extract protein ID
                protein_id = entry.get("primaryAccession", "unknown")
                
                # Extract protein name
                protein_name = "Unknown"
                if "proteinDescription" in entry and "recommendedName" in entry["proteinDescription"]:
                    if "fullName" in entry["proteinDescription"]["recommendedName"]:
                        protein_name = entry["proteinDescription"]["recommendedName"]["fullName"].get("value", "Unknown")
                
                # Extract organism
                organism = "Unknown"
                if "organism" in entry and "scientificName" in entry["organism"]:
                    organism = entry["organism"]["scientificName"]
                
                # Extract sequence
                sequence = entry.get("sequence", {}).get("value", "")
                
                if not sequence:
                    print(f"Warning: No sequence found for {protein_id}")
                    continue
                
                # Write to FASTA format
                header = f">{protein_id} {protein_name} OS={organism}"
                fasta_file.write(f"{header}\n")
                
                # Write sequence with line breaks every 60 characters
                for i in range(0, len(sequence), 60):
                    fasta_file.write(f"{sequence[i:i+60]}\n")
                    
                fasta_file.write("\n")
        
        if len(data) == 0:
            return {"error": "No results found in the Uniprot query."}

        return {"top_id": data[0].get("primaryAccession", "unknown"), "record_count": len(data)}



if __name__ == '__main__':
    # Test
    uniprot_query = UniprotQuery(BASE_DIR)
    
    input_args = {
        "keyword": "RBD Omicron",
    }

    for obs in uniprot_query.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # uniprot_fetch_sequence.terminate()
    