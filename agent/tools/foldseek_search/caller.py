import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import pandas as pd

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)


@register_tool
class FoldseekSearch(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/foldseek_search", **kwargs):
        """
        Initializes the FoldseekSearch tool wrapper.
        """
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        self.tool_name = self.config.document["tool_name"]
    
    def __call__(self, query_pdb_path: str, database: str = "PDB", max_results: int = 100, evalue_threshold: float = 1e-3) -> dict:
        """
        Executes the foldseek search tool to find structurally similar proteins.
        
        Args:
            query_pdb_path (str): Path to the query PDB file
            database_path (str): Path to the database or "PDB" for default
            max_results (int): Maximum number of results to return
            evalue_threshold (float): E-value threshold for filtering results
            
        Returns:
            dict: A dictionary containing search results and statistics
        """
        # --- Input Validation ---
        query_abs_path = os.path.join(self.out_dir, query_pdb_path) if not os.path.isabs(query_pdb_path) else query_pdb_path
        
        if not os.path.exists(query_abs_path):
            return {"error": f"Input query PDB file not found at path: {query_pdb_path}"}
        
        start_time = datetime.datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        
        query_basename = os.path.basename(query_pdb_path).split('.')[0]
        save_dir = f"{self.out_dir}/foldseek_search/{timestamp}"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # Handle database path - support default PDB database
        if database.upper() == "PDB":
            database_path = self.config.get("default_database", f"dataset/pdb")
            # Replace ROOT_DIR template with actual path
            database_path = os.path.join(ROOT_DIR, database_path)
            
        else:
            return {"error": f"Unsupported database: {database}."}
        
        foldseek_path = self.config["bin"]
        script_path = f'{BASE_DIR}/{self.config["script"]}'

        result_path = os.path.join(save_dir, f"{query_basename}_search_results.tsv")

        script_args = [
            foldseek_path, 
            query_abs_path, 
            database_path, 
            result_path,
            str(max_results),
            str(evalue_threshold)
        ]
        
        cmd = [f"cd {ROOT_DIR} && "] + [script_path] + script_args
        cmd = " ".join(cmd)
        
        # Redirect stdout and stderr to self.log_path for proper logging
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            
            if os.path.exists(result_path):
                
                duration = (datetime.datetime.now() - start_time).total_seconds()
                
                
                if os.path.getsize(result_path) == 0:
                    result = {
                        "results_df_path": result_path.replace(f"{self.out_dir}/", "", 1),
                        "top_structure_info": {},
                        "total_hits": 0,
                        "duration": duration,
                        "error": "No hits found in the search results."
                    }
                    return result
                
                
                
                # Read the search results
                df = pd.read_csv(result_path, sep='\t', header=None)
                df.columns = ['query', 'target', 'pident', 'alnlen', 'mismatch', 
                             'gapopen', 'qstart', 'qend', 'tstart', 'tend', 'evalue', 'bits']
                
                
                # Get the best hit (highest bit score)
                best_hit = df.loc[df['bits'].idxmax()]
                top_structure_info = {
                    "target_id": best_hit['target'],
                    "sequence_identity": float(best_hit['pident']),
                    "alignment_length": int(best_hit['alnlen']),
                    "mismatches": int(best_hit['mismatch']),
                    "gap_opens": int(best_hit['gapopen']),
                    "query_start": int(best_hit['qstart']),
                    "query_end": int(best_hit['qend']),
                    "target_start": int(best_hit['tstart']),
                    "target_end": int(best_hit['tend']),
                    "evalue": float(best_hit['evalue']),
                    "bit_score": float(best_hit['bits'])
                }
                
                # Calculate statistics
                total_hits = len(df)
                avg_evalue = float(df['evalue'].mean())
                avg_identity = float(df['pident'].mean())
                
                result = {
                    "results_df_path": result_path.replace(f"{self.out_dir}/", "", 1),
                    "top_target_id": top_structure_info["target_id"],
                    "top_target_seqid": top_structure_info["sequence_identity"],
                    "top_target_evalue": top_structure_info["evalue"],
                    "top_target_bitscore": top_structure_info["bit_score"],
                    "total_hits": total_hits,
                    "avg_evalue": avg_evalue,
                    "avg_identity": avg_identity,
                    "duration": duration
                }
                
                return result
                
            else:
                return {"error": f"Foldseek search failed. "}
                
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


if __name__ == '__main__':
    foldseek_search = FoldseekSearch(BASE_DIR)
    
    input_args = {
        "query_pdb_path": "example/query_example.pdb",
        "database_path": "PDB",
        "max_results": 10,
        "evalue_threshold": 10.0
    }
    
    for obs in foldseek_search.mp_run(**input_args):
        os.system("clear")
        print(obs)
