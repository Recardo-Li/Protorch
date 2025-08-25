import os
import re

from rdkit import Chem
import requests


aa_set = {"A", "C", "D", "E", "F", "G", "H", "I", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U", "V", "W", "Y"}
foldseek_set = {"p", "y", "n", "w", "r", "q", "h", "g", "d", "l", "v", "t", "m", "f", "s", "a", "e", "i", "k", "c", "#"}

uniprot_pattern = r"^(?:[OPQ][0-9][A-Z0-9]{4}|[A-NR-Z][0-9][A-Z0-9]{4}|F[0-9][A-Z0-9]{4}|A\d[A-Z]\d[A-Z0-9]{6})$"
pdb_pattern = r"^(?:[A-Z0-9]{4}|[A-Z][A-Z0-9]{4})$"
pfam_pattern = r"^PF\d{5}(\.\d+)?$"
# 1. Define the "sub-unit" pattern, which is the basic building block.
#    Order is important: match more specific patterns (like 'A1-10') before general ones ('A').
subunit = r"(?:[A-Z]\d+-\d+|\d+-\d+|[A-Z]|\d+)"

# 2. Compile the full pattern. This reads as:
#    ^                  - Start of string
#    (subunit)          - A mandatory first sub-unit
#    (?:/(subunit))*    - Optionally followed by '/' and more sub-units (forms a "segment")
#    (?::(segment))*    - Optionally followed by ':' and more segments
#    $                  - End of string
non_empty_contig = fr"{subunit}(?:/{subunit})*(?::{subunit}(?:/{subunit})*)*"
contig_pattern = fr"^(?:{non_empty_contig})?$"

mutinfo_pattern = r"^([ACDEFGHIKLMNPQSTVWY]\d+[ACDEFGHIKLMNPQSTVWY])(?::[ACDEFGHIKLMNPQSTVWY]\d+[ACDEFGHIKLMNPQSTVWY])*$"

uniprot_subsection = {
    "Active site", "Binding site", "Site", "DNA binding", "Natural variant", "Mutagenesis",
    "Transmembrane", "Topological domain", "Intramembrane", "Signal peptide", "Propeptide",
    "Transit peptide", "Chain", "Peptide", "Modified residue", "Lipidation", "Glycosylation",
    "Disulfide bond", "Cross-link", "Domain", "Repeat", "Compositional bias", "Region", "Coiled coil",
    "Motif","Function", "Miscellaneous", "Caution", "Catalytic activity", "Cofactor",
    "Activity regulation", "Biophysicochemical properties", "Pathway", "Involvement in disease",
    "Allergenic properties", "Toxic dose", "Pharmaceutical use", "Disruption phenotype",
    "Subcellular location", "Post-translational modification", "Subunit", "Domain (non-positional annotation)",
    "Sequence similarities", "RNA Editing", "Tissue specificity", "Developmental stage", "Induction",
    "Biotechnology", "Polymorphism", "GO annotation", "Proteomes", "Protein names", "Gene names",
    "Organism", "Taxonomic lineage", "Virus host"
}


def type_check(name: str, value: str, detailed_type: str, file_dir: str) -> str:
    """
    Check if the value is of the specified type
    Args:
        name: The name of the parameter

        value: The value to check
        
        detailed_type: Check whether the value is of the specified type

        file_dir: The directory where the file is located. Used for checking if the file exists
        
    Returns:
        bool: True if the value is of the specified type, False otherwise
    """
    error_type = None
    if value is None:
        return f"Parameter {name} is None."

    if detailed_type == "A3M_PATH":
        if not value.endswith(".a3m"):
            error_type = "type"

        elif not os.path.exists(os.path.join(file_dir, value)):
            error_type = "existence"

    elif detailed_type == "FASTA_PATH":
        if not value.endswith((".fasta", ".fa")):
            error_type = "type"

        elif not os.path.exists(os.path.join(file_dir, value)):
            error_type = "existence"

    elif detailed_type == "HMM_PATH":
        if not value.endswith(".hmm"):
            error_type = "type"

        elif not os.path.exists(os.path.join(file_dir, value)):
            error_type = "existence"

    elif detailed_type == "AA_SEQUENCE":
        for aa in value:
            if aa == ' ' or aa == '\n':
                continue
            if aa not in aa_set:
                error_type = "type"

    elif detailed_type == "FOLDSEEK_SEQUENCE":
        for token in value:
            if token not in foldseek_set:
                error_type = "type"

    elif detailed_type == "FULL_STRUCTURE_PATH":
        if not value.endswith((".pdb", ".cif")):
            error_type = "type"

        elif not os.path.exists(os.path.join(file_dir, value)):
            error_type = "existence"

    elif detailed_type == "PDB_ID":
        url = f"https://files.rcsb.org/download/{value}.cif"
        try:
            response = requests.head(url, timeout=30)
            if response.status_code in [200, 302, 303, 307]:
                pass
            else:
                error_type = "type"
        except:
            error_type = "type"
        # if not re.match(pdb_pattern, value):
        #     error_type = "type"

    elif detailed_type == "UNIPROT_ID":
        if not re.match(uniprot_pattern, value):
            error_type = "type"

    elif detailed_type == "PFAM_ID":
        if not re.match(pfam_pattern, value):
            error_type = "type"

    elif detailed_type == "UNIPROT_SUBSECTION":
        pass

    elif detailed_type == "SMILES":
        try:
            Chem.MolFromSmiles(value)
        except Exception:
            error_type = "type"

    elif detailed_type == "RFDIFFUSION_CONTIGS":
        if not re.match(contig_pattern, value):
            error_type = "type"
        # pass
    
    elif detailed_type == "MUTATION_INFO":
        if not re.match(mutinfo_pattern, value):
            error_type = "type"
    
    # Other types can be ignored for now
    else:
        pass

    # Return error message if the type check fails
    if error_type == "type":
        return f"Parameter {name} has wrong type, expected {detailed_type}."

    elif error_type == "existence":
        return f"File {value} does not exist."

    else:
        return None