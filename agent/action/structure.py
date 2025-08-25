import os
import re
from string import ascii_lowercase, ascii_uppercase
import time

from typing import List
from .config import get_temp_dir
from lagent.actions.base_action import BaseAction, tool_api
from Bio.PDB import PDBParser, FastMMCIFParser, Atom, Model, Structure, Chain, Residue
from Bio.PDB.PDBIO import PDBIO
from Bio.PDB.mmcifio import MMCIFIO
import py3Dmol

from data.utils.parse import is_residue_valid, get_chain_ids



mmcif_parser = FastMMCIFParser(QUIET=True)
mmcif_io = MMCIFIO()
pdb_parser = PDBParser(QUIET=True)
pdb_io = PDBIO()
aa3to1 = {'CYS': 'C', 'ASP': 'D', 'SER': 'S', 'GLN': 'Q', 'LYS': 'K',
          'ILE': 'I', 'PRO': 'P', 'THR': 'T', 'PHE': 'F', 'ASN': 'N',
          'GLY': 'G', 'HIS': 'H', 'LEU': 'L', 'ARG': 'R', 'TRP': 'W',
          'ALA': 'A', 'VAL': 'V', 'GLU': 'E', 'TYR': 'Y', 'MET': 'M'}
aa1to3 = {v: k for k, v in aa3to1.items()}
pymol_color_list = ["#33ff33","#00ffff","#ff33cc","#ffff00","#ff9999","#e5e5e5","#7f7fff","#ff7f00",
          "#7fff7f","#199999","#ff007f","#ffdd5e","#8c3f99","#b2b2b2","#007fff","#c4b200",
          "#8cb266","#00bfbf","#b27f7f","#fcd1a5","#ff7f7f","#ffbfdd","#7fffff","#ffff7f",
          "#00ff7f","#337fcc","#d8337f","#bfff3f","#ff7fff","#d8d8ff","#3fffbf","#b78c4c",
          "#339933","#66b2b2","#ba8c84","#84bf00","#b24c66","#7f7f7f","#3f3fa5","#a5512b"]

alphabet_list = list(ascii_uppercase+ascii_lowercase)
    

class StructureOperator(BaseAction):
    """
    Ensemble operations for Protein Structure.
    """
    @tool_api
    def visualize(self, structure_path: str) -> dict:
        """
        Visualizes a structure file. When the result is a protein structure, this tool provides a visualization for the user. Typically, it is used only once per unique structure path.

        Args:
            structure_path (str): Path to the pdb file.
        
        Returns:
            html: The visualized html file path.
        """
        assert os.path.exists(structure_path), f"Error: {structure_path} does not exist!"
        
    
        file_type = str(structure_path).split(".")[-1]
        if file_type == "cif":
            file_type == "mmcif"

        view = py3Dmol.view(js='https://3dmol.org/build/3Dmol.js',)
        view.addModel(open(structure_path,'r').read(),file_type)

        view.setStyle({'cartoon': {'color':'spectrum'}})
        # if color == "lDDT":
            # view.setStyle({'cartoon': {'colorscheme': {'prop':'b','gradient': 'roygb','min':50,'max':90}}})
        # elif color == "rainbow":
        #     view.setStyle({'cartoon': {'color':'spectrum'}})
        # elif color == "chain":
        #     chains = len(get_chain_ids(structure_path))
        #     for n,chain,color in zip(range(chains),alphabet_list,pymol_color_list):
        #         view.setStyle({'chain':chain},{'cartoon': {'color':color}})

        # if show_sidechains:
        #     BB = ['C','O','N']
        #     view.addStyle({'and':[{'resn':["GLY","PRO"],'invert':True},{'atom':BB,'invert':True}]},
        #                         {'stick':{'colorscheme':f"WhiteCarbon",'radius':0.3}})
        #     view.addStyle({'and':[{'resn':"GLY"},{'atom':'CA'}]},
        #                         {'sphere':{'colorscheme':f"WhiteCarbon",'radius':0.3}})
        #     view.addStyle({'and':[{'resn':"PRO"},{'atom':['C','O'],'invert':True}]},
        #                         {'stick':{'colorscheme':f"WhiteCarbon",'radius':0.3}})
        # if show_mainchains:
        #     BB = ['C','O','N','CA']
        #     view.addStyle({'atom':BB},{'stick':{'colorscheme':f"WhiteCarbon",'radius':0.3}})

        output_path = f"outputs/{structure_path.split('/')[-1].split('.')[0]}.html"
        view.zoomTo()
        
        html_content = view._make_html()
        html_content_modified = re.sub(
            r'(<div id="3dmolviewer_\d+"  style=")[^"]*(">)',
            r'\1position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 100%; height: 100%; display: flex; justify-content: center; align-items: center;\2',
            html_content
        )
        # 将修改后的 HTML 内容写入文件
        with open(output_path, 'w') as f:
            f.write(html_content_modified)
        
        return {"html": output_path}

    # @tool_api
    # def load(self, structure_path: str, chains: list = None, CA_only: bool = False) -> dict:
        """
        Parse a structure file into a list of dict. Don't use this tool unless the user require seeing the contents inside the structure file.

        Args:
            structure_path (str): Path to the pdb file.

            chains (list): A list of chains to be parsed. If None, all chains will be parsed.

            CA_only (bool): If True, only CA atoms will be parsed.

        Returns:
            A dict of parsed chains. The keys are chain ids and the values are dicts of parsed chains.
                seq: Amino acid sequence of the chain.
                coords: A dict of coordinates of the chain. The keys are "N", "CA", "C", "O".
                name: Name of the pdb.
                chain: Chain ID.
        """
        assert os.path.exists(structure_path), f"Error: {structure_path} does not exist!"
        

        _, file = os.path.split(structure)
        name, format = os.path.splitext(file)

        assert format in ['.pdb', '.cif'], "Only support pdb and mmcif format"
        
        parser = pdb_parser if format == ".pdb" else mmcif_parser
        structure = parser.get_structure(name, structure_path)

        parsed_dicts = {}
        chains = structure[0].get_chains() if chains is None else [structure[0][chain_id] for chain_id in chains]
        for chain in chains:
            residues = chain.get_residues()
            atoms = ['N', 'CA', 'C', 'O'] if not CA_only else ['CA']
            coords = {atom: [] for atom in atoms}

            seq = []
            for residue in residues:
                if is_residue_valid(residue, CA_only):
                    res_name = residue.get_resname()
                    seq.append(aa3to1[res_name])
                    for atom in atoms:
                        coords[atom].append(residue[atom].get_coord().tolist())

            parsed_dict = {"name": name,
                        "chain": chain.get_id(),
                        "seq": "".join(seq),
                        "coords": coords}
            
            # Skip empty chains
            if len(parsed_dict["seq"]) != 0:
                parsed_dicts[chain.get_id()] = parsed_dict

        return parsed_dicts