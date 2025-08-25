import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import shlex
import re

from Bio.Blast import NCBIXML
from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Blast(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/blast", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, query_sequence, blast_program="blastp", blast_database="nr", hitlist_size=50, expect_value=10) -> dict:
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        save_path = f"{self.out_dir}/blast/{now}/result.xml"
        fasta_path = f"{self.out_dir}/blast/{now}/result.fasta"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        cmd_args = {
            "query_sequence": query_sequence,
            "blast_program": blast_program,
            "blast_database": blast_database,
            "hitlist_size": hitlist_size,
            "expect_value":expect_value,
            "save_path": save_path,
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            if isinstance(v, str):
                v = shlex.quote(v)
            cmd += f" --{k} {v}"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)  
        
            spend_time = (datetime.datetime.now() - start).total_seconds()
            # if run successfully, check the log info
            if os.path.exists(save_path):
                
                results = {"blast_xml": save_path[len(self.out_dir)+1:], "blast_fasta": fasta_path[len(self.out_dir)+1:], "duration": spend_time}
                scores = self._process_blast_xml(save_path, output_fasta=fasta_path)
                if 'error' in scores:
                    return {'error': scores['message']}
                elif scores.get("hit_count", 0) == 0:
                    return {'error': "No hit for this sequence"}
                else:
                    results.update(scores)
                    return results
            else:
                return {"error": "Failed to run blast"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def _process_blast_xml(self, xml_file, output_fasta=None):
        """
        Parse a BLAST XML file to extract hit count and top hit ID,
        and write all hit sequences to a FASTA file with simplified headers.
        
        Args:
            xml_file (str): Path to the BLAST XML result file
            output_fasta (str, optional): Path to output FASTA file. If None, 
                                        will use xml_file name with .fasta extension
        
        Returns:
            dict: Dictionary containing hit_count and top_hit_id
        """

        
        # Check if file exists
        if not os.path.exists(xml_file):
            raise FileNotFoundError(f"BLAST XML file not found: {xml_file}")
        
        # Set default output filename if not provided
        if output_fasta is None:
            base_name = os.path.splitext(xml_file)[0]
            output_fasta = f"{base_name}.fasta"
        
        result = {
            'hit_count': 0,
            'top_hit_id': None,
        }
        
        # Parse the XML file and write hits to FASTA
        with open(xml_file) as result_handle, open(output_fasta, 'w') as fasta_out:
            try:
                blast_record = NCBIXML.read(result_handle)
                
                # Count hits
                result['hit_count'] = len(blast_record.alignments)
                
                # Get top hit ID if available
                if result['hit_count'] > 0:
                    result['top_hit_id'] = blast_record.alignments[0].hit_id
                
                # Write all hits to FASTA file with simplified headers
                for alignment in blast_record.alignments:
                    hit_id = alignment.hit_id
                    hit_def = alignment.hit_def
                    
                    # Simplify the header
                    simplified_header = self._simplify_fasta_header(hit_id, hit_def)
                    
                    # Use the first HSP sequence for each hit
                    if alignment.hsps:
                        hsp = alignment.hsps[0]  # Get the first (best) HSP
                        sequence = hsp.sbjct
                        
                        # Write to FASTA format with simplified header
                        fasta_out.write(f">{simplified_header}\n")
                        
                        # Write sequence in chunks of 60 characters
                        for i in range(0, len(sequence), 60):
                            fasta_out.write(f"{sequence[i:i+60]}\n")
                
                return result
                
            except Exception as e:
                error_info = {
                    'error': True,
                    'message': f"Error processing BLAST XML file: {str(e)}",
                    'hit_count': 0,
                    'top_hit_id': None
                }
                return error_info

    def _simplify_fasta_header(self, hit_id, hit_def):
        """
        Simplify FASTA header by extracting the most important information.
        
        Args:
            hit_id (str): The hit ID from BLAST
            hit_def (str): The hit definition from BLAST
            
        Returns:
            str: A simplified FASTA header
        """
        # Extract the first accession number
        accession_match = re.search(r'([a-zA-Z]+\|[a-zA-Z0-9_.]+)', hit_id)
        accession = accession_match.group(1) if accession_match else hit_id
        
        # Extract the protein name and organism
        protein_match = re.search(r'([^\[]+)\[([^\]]+)\]', hit_def)
        
        if protein_match:
            protein_name = protein_match.group(1).strip()
            organism = protein_match.group(2).strip()
            
            # Further simplify protein name if it's too long
            if len(protein_name) > 30:
                protein_name = protein_name.split(',')[0].strip()
                protein_name = protein_name.split('(')[0].strip()
            
            return f"{accession} {protein_name} [{organism}]"
        else:
            # If regex doesn't match, use a more basic approach
            # Take first 50 chars of hit_def if it's too long
            short_def = hit_def[:50] + "..." if len(hit_def) > 50 else hit_def
            return f"{accession} {short_def}"



if __name__ == '__main__':
    # Test
    blast = Blast(BASE_DIR)
    
    input_args = {
        "query_sequence": "AAA",
    }

    for obs in blast.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # blast.terminate()
    