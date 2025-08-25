"""
Storing constants
"""

import json
ROOT_DIR = __file__.rsplit("/", 2)[0]

# toolset
doc_format = {
    "general_keys": [
        "category_name",
        "tool_name",
        "tool_description",
        "required_parameters",
        "optional_parameters",
        "return_values",
    ],
    "para_keys": ["required_parameters", "optional_parameters"],
    "para_infos": ["name", "type", "description"],
    "specific_key_dict": {},
    "para_types": ["TEXT", "SEQUENCE", "STRUCTURE", "PARAMETER", "PREDICTION", "SELECTION", "MOLECULE"],
}
with open(f"{ROOT_DIR}/funchub/available_paras.json") as fp:
    doc_format["para_dict"] = json.load(fp)


# value contents
struc_extensions = [".pdb", ".mol", ".mol2", ".sdf", ".cif", ".xyz", ".mmcif"]
seq_extensions = [
    # MSA-specific formats
    ".aln",  # Clustal format alignment file
    ".fasta",  # FASTA format for MSA and general sequence files
    ".fa",  # FASTA format shorthand
    ".msf",  # Multiple Sequence File (GCG format)
    ".phylip",  # PHYLIP format
    ".phy",  # PHYLIP shorthand
    ".nex",  # NEXUS format
    ".nexus",  # NEXUS full format name
    ".stockholm",  # Stockholm format
    ".sth",  # Stockholm shorthand
    ".a2m",  # Alignment to Model format
    ".maf",  # Multiple Alignment Format
    ".fsa",  # FASTA format variant for MSA
    ".pfam",  # Specific format used by the Pfam database
    # General sequence formats
    ".gb",  # GenBank format
    ".gbk",  # GenBank format (alternative extension)
    ".embl",  # EMBL format (European Molecular Biology Laboratory)
    ".gff",  # General Feature Format (GFF)
    ".gff3",  # GFF version 3
    ".vcf",  # Variant Call Format
    ".sam",  # Sequence Alignment/Map format
    ".bam",  # Binary version of SAM format
    ".cram",  # Compressed version of SAM/BAM format
    ".bed",  # BED format for genomic regions
    ".wig",  # WIG format for continuous data
    ".fastq",  # FASTQ format for sequences with quality scores
    ".qual",  # Quality scores (paired with FASTA)
    ".sff",  # Standard Flowgram Format (for 454 sequencing)
    ".ace",  # ACE format for assembly
    ".pdb",  # Protein Data Bank format for 3D structures
    ".hmm",  # Hidden Markov Model format (used in HMMER)
    ".xml",  # XML-based formats, including SBML and others
    ".clu",  # CLUSTAL format
    ".seq",  # Generic sequence format
    ".cns",  # CN3D format (NCBI)
    ".json",  # JSON format for structured sequence data
    ".a3m",  # A3M format, a multiple sequence alignment format often used in homology modeling and structural prediction
    ".hhr",  # HHR format, output from HHsearch, a tool for sequence comparison and profile-based alignments
]

mol_extensions = [
    ".smi",  # SMILES format (Simplified Molecular Input Line Entry System)
    ".smiles",  # SMILES full format name
    ".pdb",  # Protein Data Bank format for 3D structures
    ".mol",  # MDL MOL format for 2D/3D structures
    ".mol2",  # Tripos MOL2 format for detailed structures
    ".sdf",  # Structure Data File (based on MOL format, supports multiple molecules)
    ".xyz",  # XYZ format for atomic coordinates
    ".cif",  # Crystallographic Information File for crystal structures
    ".pqr",  # PQR format with atomic charges and radii
    ".gro",  # GROMACS format for molecular dynamics
    ".top",  # Topology format for molecular dynamics (GROMACS)
    ".cml",  # Chemical Markup Language, XML-based format
    ".inchi",  # IUPAC International Chemical Identifier
    ".cdx",  # ChemDraw binary format
    ".cdxml",  # ChemDraw XML format
    ".mae",  # Maestro format (Schrödinger software)
    ".mmod",  # Macromodel format (Schrödinger software)
    ".mrv",  # Marvin (ChemAxon) format
    ".rdf",  # Reaction Data File (MDL format for reactions)
    ".rxn",  # MDL Reaction format
    ".sd",  # Short for SDF (Structure Data File)
]

seq_pattern = r"(^([ABCDEFGHIKLMNOPQRSTUVWXYZ.-][#pynwrqhgdlvtmfsaeikc])+$)|(^[ABCDEFGHIKLMNOPQRSTUVWXYZ.-]+$)"
aa3to1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLU": "E",
    "GLN": "Q",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}
