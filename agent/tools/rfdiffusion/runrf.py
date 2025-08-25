import os
import argparse
import time
import json
import numpy as np
import matplotlib.pyplot as plt
import signal
import sys
from Bio import PDB, SeqIO
from Bio.PDB import MMCIFParser, PDBParser, Residue
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.tools.rfdiffusion import residue_constants

# from rfdiffusion.inference.utils import parse_pdb


MODRES = {
    "MSE": "MET",
    "MLY": "LYS",
    "FME": "MET",
    "HYP": "PRO",
    "TPO": "THR",
    "CSO": "CYS",
    "SEP": "SER",
    "M3L": "LYS",
    "HSK": "HIS",
    "SAC": "SER",
    "PCA": "GLU",
    "DAL": "ALA",
    "CME": "CYS",
    "CSD": "CYS",
    "OCS": "CYS",
    "DPR": "PRO",
    "B3K": "LYS",
    "ALY": "LYS",
    "YCM": "CYS",
    "MLZ": "LYS",
    "4BF": "TYR",
    "KCX": "LYS",
    "B3E": "GLU",
    "B3D": "ASP",
    "HZP": "PRO",
    "CSX": "CYS",
    "BAL": "ALA",
    "HIC": "HIS",
    "DBZ": "ALA",
    "DCY": "CYS",
    "DVA": "VAL",
    "NLE": "LEU",
    "SMC": "CYS",
    "AGM": "ARG",
    "B3A": "ALA",
    "DAS": "ASP",
    "DLY": "LYS",
    "DSN": "SER",
    "DTH": "THR",
    "GL3": "GLY",
    "HY3": "PRO",
    "LLP": "LYS",
    "MGN": "GLN",
    "MHS": "HIS",
    "TRQ": "TRP",
    "B3Y": "TYR",
    "PHI": "PHE",
    "PTR": "TYR",
    "TYS": "TYR",
    "IAS": "ASP",
    "GPL": "LYS",
    "KYN": "TRP",
    "CSD": "CYS",
    "SEC": "CYS",
}

num2aa = [
    "ALA",
    "ARG",
    "ASN",
    "ASP",
    "CYS",
    "GLN",
    "GLU",
    "GLY",
    "HIS",
    "ILE",
    "LEU",
    "LYS",
    "MET",
    "PHE",
    "PRO",
    "SER",
    "THR",
    "TRP",
    "TYR",
    "VAL",
    "UNK",
    "MAS",
]

aa2num = {x: i for i, x in enumerate(num2aa)}


aa2long = [
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "3HB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # ala
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD ",
        " NE ",
        " CZ ",
        " NH1",
        " NH2",
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "1HG ",
        "2HG ",
        "1HD ",
        "2HD ",
        " HE ",
        "1HH1",
        "2HH1",
        "1HH2",
        "2HH2",
    ),  # arg
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " OD1",
        " ND2",
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "1HD2",
        "2HD2",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # asn
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " OD1",
        " OD2",
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # asp
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " SG ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        " HG ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # cys
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD ",
        " OE1",
        " NE2",
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "1HG ",
        "2HG ",
        "1HE2",
        "2HE2",
        None,
        None,
        None,
        None,
        None,
    ),  # gln
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD ",
        " OE1",
        " OE2",
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "1HG ",
        "2HG ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # glu
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        "1HA ",
        "2HA ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # gly
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " ND1",
        " CD2",
        " CE1",
        " NE2",
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        " HD2",
        " HE1",
        " HE2",
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # his
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG1",
        " CG2",
        " CD1",
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        " HB ",
        "1HG2",
        "2HG2",
        "3HG2",
        "1HG1",
        "2HG1",
        "1HD1",
        "2HD1",
        "3HD1",
        None,
        None,
    ),  # ile
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD1",
        " CD2",
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        " HG ",
        "1HD1",
        "2HD1",
        "3HD1",
        "1HD2",
        "2HD2",
        "3HD2",
        None,
        None,
    ),  # leu
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD ",
        " CE ",
        " NZ ",
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "1HG ",
        "2HG ",
        "1HD ",
        "2HD ",
        "1HE ",
        "2HE ",
        "1HZ ",
        "2HZ ",
        "3HZ ",
    ),  # lys
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " SD ",
        " CE ",
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "1HG ",
        "2HG ",
        "1HE ",
        "2HE ",
        "3HE ",
        None,
        None,
        None,
        None,
    ),  # met
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD1",
        " CD2",
        " CE1",
        " CE2",
        " CZ ",
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        " HD1",
        " HD2",
        " HE1",
        " HE2",
        " HZ ",
        None,
        None,
        None,
        None,
    ),  # phe
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " HA ",
        "1HB ",
        "2HB ",
        "1HG ",
        "2HG ",
        "1HD ",
        "2HD ",
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # pro
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " OG ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HG ",
        " HA ",
        "1HB ",
        "2HB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # ser
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " OG1",
        " CG2",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HG1",
        " HA ",
        " HB ",
        "1HG2",
        "2HG2",
        "3HG2",
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # thr
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD1",
        " CD2",
        " NE1",
        " CE2",
        " CE3",
        " CZ2",
        " CZ3",
        " CH2",
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        " HD1",
        " HE1",
        " HZ2",
        " HH2",
        " HZ3",
        " HE3",
        None,
        None,
        None,
    ),  # trp
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG ",
        " CD1",
        " CD2",
        " CE1",
        " CE2",
        " CZ ",
        " OH ",
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        " HD1",
        " HE1",
        " HE2",
        " HD2",
        " HH ",
        None,
        None,
        None,
        None,
    ),  # tyr
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        " CG1",
        " CG2",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        " HB ",
        "1HG1",
        "2HG1",
        "3HG1",
        "1HG2",
        "2HG2",
        "3HG2",
        None,
        None,
        None,
        None,
    ),  # val
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "3HB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # unk
    (
        " N  ",
        " CA ",
        " C  ",
        " O  ",
        " CB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        " H  ",
        " HA ",
        "1HB ",
        "2HB ",
        "3HB ",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ),  # mask
]


def is_standard_residue(res_name):
    standard_protein = {
        "ALA",
        "ARG",
        "ASN",
        "ASP",
        "CYS",
        "GLN",
        "GLU",
        "GLY",
        "HIS",
        "ILE",
        "LEU",
        "LYS",
        "MET",
        "PHE",
        "PRO",
        "SER",
        "THR",
        "TRP",
        "TYP",
        "TYR",
        "VAL",
    }
    standard_rna = {"A", "U", "G", "C", "DA", "DU", "DG", "DC"}
    return res_name in standard_protein or res_name in standard_rna


def write_atom_lines(residue: Residue, record="ATOM  "):
    atom_lines = []
    for atom in residue:
        x, y, z = (
            format(atom.coord[0], "8.3f"),
            format(atom.coord[1], "8.3f"),
            format(atom.coord[2], "8.3f"),
        )
        serial = format(atom.serial_number, "5d")
        name = atom.name.ljust(4)
        alternate_id = atom.altloc if atom.altloc else " "
        res_name = residue.resname.ljust(3)
        chain_id = residue.get_parent().id if hasattr(residue, "get_parent") else " "
        res_seq = format(residue.id[1], "4d")
        insertion_code = residue.id[2] if len(residue.id) > 2 else " "
        occupancy = format(atom.occupancy, "6.2f")
        temp_factor = format(atom.bfactor, "6.2f")
        segment_id = residue.segid.ljust(4) if hasattr(residue, "segid") else "    "
        element = atom.element.rjust(2) if atom.element else "  "
        charge = atom.charge if hasattr(atom, "charge") else "  "

        # 根据 PDB 格式拼接各字段
        line = (
            f"{record}{serial} {name}{alternate_id}{res_name} {chain_id}{res_seq}{insertion_code}   "
            f"{x}{y}{z}{occupancy}{temp_factor}      {segment_id}{element}{charge}\n"
        )
        atom_lines.append(line)
    return atom_lines


def structure2pdb(structure_file, chains=None, models=None):
    """
    读取mmcif文件并返回字符串格式的结构，支持筛选特定链和模型。
    参数：
        mmcif_file: string，文件路径或包含内容的字符串
        chains: list[string] or None，要保留的链号列表，默认保留所有链
        models: list[int] or None，要保留的模型编号列表，默认保留所有模型
    返回：
        str, 包含ATOM、HETATM、TER和MODEL条目的PDB格式字符串
    """
    if structure_file.endswith(".cif"):
        parser = PDB.MMCIFParser()
    elif structure_file.endswith(".pdb"):
        parser = PDB.PDBParser(QUIET=True)
    else:
        raise ValueError(
            "Unsupported file format. Please provide a .cif or .pdb file."
        )
    structure = parser.get_structure("unknown", structure_file)

    lines = []
    for model in structure:
        if models is not None and int(model.id) not in models:
            continue  # 跳过不在指定模型中的条目

        for chain in model:
            chain_id = chain.get_id()
            if chains is not None and chain_id not in chains:
                continue  # 跳过不在指定链中的条目
            prev_residue_id = None
            for residue in chain:
                res_type = residue.resname.strip().upper()
                if not is_standard_residue(res_type):
                    lines.extend(write_atom_lines(residue, "HETATM"))
                else:
                    lines.extend(write_atom_lines(residue))
                if (
                    prev_residue_id is not None
                    and residue.get_id()[1] != prev_residue_id[1] + 1
                ):
                    # 如果当前残基的序号与前一个残基不连续，添加TER行
                    ter_line = f"TER            {chain_id}\n"
                    lines.append(ter_line)
                prev_residue_id = residue.get_id()

            # 在每个链的末尾添加TER行
            ter_line = f"TER            {chain.get_id():1s}\n"
            lines.append(ter_line)

        model_line = f"MODEL {model.id}\n"
        if models is not None and len(models) > 1:
            lines.insert(lines.index("TER\n"), model_line)
            # TODO: 这里可能需要更精确地插入

        endmdl_line = f"ENDMDL\n"

        lines.append(endmdl_line)
    return "".join(lines)


def sym_it(coords, center, cyclic_symmetry_axis, reflection_axis=None):

    def rotation_matrix(axis, theta):
        axis = axis / np.linalg.norm(axis)
        a = np.cos(theta / 2)
        b, c, d = -axis * np.sin(theta / 2)
        return np.array(
            [
                [
                    a * a + b * b - c * c - d * d,
                    2 * (b * c - a * d),
                    2 * (b * d + a * c),
                ],
                [
                    2 * (b * c + a * d),
                    a * a + c * c - b * b - d * d,
                    2 * (c * d - a * b),
                ],
                [
                    2 * (b * d - a * c),
                    2 * (c * d + a * b),
                    a * a + d * d - b * b - c * c,
                ],
            ]
        )

    def align_axes(coords, source_axis, target_axis):
        rotation_axis = np.cross(source_axis, target_axis)
        rotation_angle = np.arccos(np.dot(source_axis, target_axis))
        rot_matrix = rotation_matrix(rotation_axis, rotation_angle)
        return np.dot(coords, rot_matrix)

    # Center the coordinates
    coords = coords - center

    # Align cyclic symmetry axis with Z-axis
    z_axis = np.array([0, 0, 1])
    coords = align_axes(coords, cyclic_symmetry_axis, z_axis)

    if reflection_axis is not None:
        # Align reflection axis with X-axis
        x_axis = np.array([1, 0, 0])
        coords = align_axes(coords, reflection_axis, x_axis)
    return coords


def fix_partial_contigs(contigs, parsed_pdb):
    INF = float("inf")

    # get unique chains
    chains = []
    for c, i in parsed_pdb["pdb_idx"]:
        if c not in chains:
            chains.append(c)

    # get observed positions and chains
    ok = []
    for contig in contigs:
        for x in contig.split("/"):
            if x[0].isalpha:
                C, x = x[0], x[1:]
                S, E = -INF, INF
                if x.startswith("-"):
                    E = int(x[1:])
                elif x.endswith("-"):
                    S = int(x[:-1])
                elif "-" in x:
                    (S, E) = (int(y) for y in x.split("-"))
                elif x.isnumeric():
                    S = E = int(x)
                for c, i in parsed_pdb["pdb_idx"]:
                    if c == C and i >= S and i <= E:
                        if [c, i] not in ok:
                            ok.append([c, i])

    # define new contigs
    new_contigs = []
    for C in chains:
        new_contig = []
        unseen = []
        seen = []
        for c, i in parsed_pdb["pdb_idx"]:
            if c == C:
                if [c, i] in ok:
                    L = len(unseen)
                    if L > 0:
                        new_contig.append(f"{L}-{L}")
                        unseen = []
                    seen.append([c, i])
                else:
                    L = len(seen)
                    if L > 0:
                        new_contig.append(f"{seen[0][0]}{seen[0][1]}-{seen[-1][1]}")
                        seen = []
                    unseen.append([c, i])
        L = len(unseen)
        if L > 0:
            new_contig.append(f"{L}-{L}")
        L = len(seen)
        if L > 0:
            new_contig.append(f"{seen[0][0]}{seen[0][1]}-{seen[-1][1]}")
        new_contigs.append("/".join(new_contig))

    return new_contigs


def fix_contigs(contigs, parsed_pdb):
    def fix_contig(contig):
        INF = float("inf")
        X = contig.split("/")
        Y = []
        for n, x in enumerate(X):
            if x[0].isalpha():
                C, x = x[0], x[1:]
                S, E = -INF, INF
                if x.startswith("-"):
                    E = int(x[1:])
                elif x.endswith("-"):
                    S = int(x[:-1])
                elif "-" in x:
                    (S, E) = (int(y) for y in x.split("-"))
                elif x.isnumeric():
                    S = E = int(x)
                new_x = ""
                c_, i_ = None, 0
                for c, i in parsed_pdb["pdb_idx"]:
                    if c == C and i >= S and i <= E:
                        if c_ is None:
                            new_x = f"{c}{i}"
                        else:
                            if c != c_ or i != i_ + 1:
                                new_x += f"-{i_}/{c}{i}"
                        c_, i_ = c, i
                Y.append(new_x + f"-{i_}")
            elif "-" in x:
                # sample length
                s, e = x.split("-")
                m = np.random.randint(int(s), int(e) + 1)
                Y.append(f"{m}-{m}")
            elif x.isnumeric() and x != "0":
                Y.append(f"{x}-{x}")
        return "/".join(Y)

    return [fix_contig(x) for x in contigs]


def parse_pdb(filename, **kwargs):
    """extract xyz coords for all heavy atoms"""
    with open(filename, "r") as f:
        lines = f.readlines()
    return parse_pdb_lines(lines, **kwargs)


def parse_pdb_lines(lines, parse_hetatom=False, ignore_het_h=True):
    # indices of residues observed in the structure
    res, pdb_idx = [], []
    for l in lines:
        if l[:4] == "ATOM" and l[12:16].strip() == "CA":
            res.append((l[22:26], l[17:20]))
            # chain letter, res num
            pdb_idx.append((l[21:22].strip(), int(l[22:26].strip())))
    seq = [aa2num[r[1]] if r[1] in aa2num.keys() else 20 for r in res]
    pdb_idx = [
        (l[21:22].strip(), int(l[22:26].strip()))
        for l in lines
        if l[:4] == "ATOM" and l[12:16].strip() == "CA"
    ]  # chain letter, res num

    # 4 BB + up to 10 SC atoms
    xyz = np.full((len(res), 14, 3), np.nan, dtype=np.float32)
    for l in lines:
        if l[:4] != "ATOM":
            continue
        chain, resNo, atom, aa = (
            l[21:22],
            int(),
            " " + l[12:16].strip().ljust(3),
            l[17:20],
        )
        if (chain, resNo) in pdb_idx:
            idx = pdb_idx.index((chain, resNo))
            # for i_atm, tgtatm in enumerate(util.aa2long[util.aa2num[aa]]):
            for i_atm, tgtatm in enumerate(aa2long[aa2num[aa]][:14]):
                if (
                    tgtatm is not None and tgtatm.strip() == atom.strip()
                ):  # ignore whitespace
                    xyz[idx, i_atm, :] = [
                        float(l[30:38]),
                        float(l[38:46]),
                        float(l[46:54]),
                    ]
                    break

    # save atom mask
    mask = np.logical_not(np.isnan(xyz[..., 0]))
    xyz[np.isnan(xyz[..., 0])] = 0.0

    # remove duplicated (chain, resi)
    new_idx = []
    i_unique = []
    for i, idx in enumerate(pdb_idx):
        if idx not in new_idx:
            new_idx.append(idx)
            i_unique.append(i)

    pdb_idx = new_idx
    xyz = xyz[i_unique]
    mask = mask[i_unique]

    seq = np.array(seq)[i_unique]

    out = {
        "xyz": xyz,  # cartesian coordinates, [Lx14]
        "mask": mask,  # mask showing which atoms are present in the PDB file, [Lx14]
        "idx": np.array(
            [i[1] for i in pdb_idx]
        ),  # residue numbers in the PDB file, [L]
        "seq": np.array(seq),  # amino acid sequence, [L]
        "pdb_idx": pdb_idx,  # list of (chain letter, residue number) in the pdb file, [L]
    }

    # heteroatoms (ligands, etc)
    if parse_hetatom:
        xyz_het, info_het = [], []
        for l in lines:
            if l[:6] == "HETATM" and not (ignore_het_h and l[77] == "H"):
                info_het.append(
                    dict(
                        idx=int(l[7:11]),
                        atom_id=l[12:16],
                        atom_type=l[77],
                        name=l[16:20],
                    )
                )
                xyz_het.append([float(l[30:38]), float(l[38:46]), float(l[46:54])])

        out["xyz_het"] = np.array(xyz_het)
        out["info_het"] = info_het

    return out


class RFExecutor:
    def __init__(
        self,
        rf_root,
        path,
        python,
        iterations=50,
        symmetry=None,
        order=1,
        hotspot=None,
        chains=None,
        num_designs=1,
    ):
        print("Initializing RFExecutor")
        print(
            f"Received parameters: rf_root={rf_root}, path={path}, python={python}, "
            f"iterations={iterations}, symmetry={symmetry}, order={order}, hotspot={hotspot}, "
            f"chains={chains}, num_designs={num_designs}"
        )
        self.rf_root = rf_root
        self.out_dir = path
        self.out_prefix = f"{path}/design"
        self.python = python
        self.iterations = iterations
        self.symmetry = symmetry
        self.order = order
        self.hotspot = hotspot
        self.chains = chains
        self.add_potential = False
        self.partial_T = "auto"
        self.num_designs = num_designs
        self.use_beta_model = False
        self.visual = None
        os.makedirs(self.out_dir, exist_ok=True)
        self.opts = [
            f"inference.output_prefix={self.out_prefix}",
            f"inference.num_designs={num_designs}",
        ]

    def get_pdb(self, pdb_code=None):
        if pdb_code is None or pdb_code == "":
            raise Exception("No PDB code provided")
        elif os.path.isfile(pdb_code):
            return pdb_code
        elif len(pdb_code) == 4:
            if not os.path.isfile(f"{self.out_dir}/{pdb_code}.pdb"):
                os.system(
                    f"wget -P {self.out_dir} -qnc https://files.rcsb.org/download/{pdb_code}.pdb.gz"
                )
                os.system(f"gunzip {self.out_dir}/{pdb_code}.pdb.gz")
            return f"{self.out_dir}/{pdb_code}.pdb"
        else:
            os.system(
                f"wget -qnc https://alphafold.ebi.ac.uk/files/AF-{pdb_code}-F1-model_v3.pdb"
            )
            return f"{self.out_dir}/AF-{pdb_code}-F1-model_v3.pdb"

    def run_ananas(self, pdb_str):
        pdb_filename = f"{self.out_dir}/ananas_input.pdb"
        out_filename = f"{self.out_dir}/ananas.json"
        with open(pdb_filename, "w") as handle:
            handle.write(pdb_str)

        cmd = f"./ananas {pdb_filename} -u -j {out_filename}"
        if self.symmetry is None:
            os.system(cmd)
        else:
            os.system(f"{cmd} {self.symmetry}")

        try:
            out = json.loads(open(out_filename, "r").read())
            results, AU = out[0], out[-1]["AU"]
            group = AU["group"]
            chains = AU["chain names"]
            rmsd = results["Average_RMSD"]
            print(f"AnAnaS detected {group} symmetry at RMSD:{rmsd:.3}")

            C = np.array(results["transforms"][0]["CENTER"])
            A = [np.array(t["AXIS"]) for t in results["transforms"]]

            new_lines = []
            for line in pdb_str.split("\n"):
                if line.startswith("ATOM"):
                    chain = line[21:22]
                    if chain in chains:
                        x = np.array([float(line[i : (i + 8)]) for i in [30, 38, 46]])
                        if group[0] == "c":
                            x = sym_it(x, C, A[0])
                        if group[0] == "d":
                            x = sym_it(x, C, A[1], A[0])
                        coord_str = "".join(["{:8.3f}".format(a) for a in x])
                        new_lines.append(line[:30] + coord_str + line[54:])
                else:
                    new_lines.append(line)
            return results, "\n".join(new_lines)

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, pdb_str

    def run(self, command, steps, num_designs=1):
        """
        Runs a command with progress tracking for designs and steps.
        """
        print("Steps =", steps)
        fail = False
        try:
            os.system(command)

        except KeyboardInterrupt:
            print("Process interrupted by user.")

        except Exception as e:
            print(f"An error occurred while running the command: {e}")
            fail = True
            
        
        finally:
            print("Run completed.")

            if fail:
                return {"error": "Failed to run RFDiffusion. Please check whether your contigs are valid."}
            else:
                output_path = f"{self.out_prefix}_0.pdb"
                return {"design": output_path}

    def run_diffusion(self, contigs, pdb, log_path=None):
        print(f"Received contigs: {contigs}")
        print(f"Received PDB: {pdb}")
        contigs = contigs.replace(",", " ").replace(":", " ").split()
        is_fixed, is_free = False, False
        fixed_chains = []
        for contig in contigs:
            for x in contig.split("/"):
                a = x.split("-")[0]
                if a[0].isalpha():
                    is_fixed = True
                    if a[0] not in fixed_chains:
                        fixed_chains.append(a[0])
                if a.isnumeric():
                    is_free = True
        if len(contigs) == 0 or not is_free:
            mode = "partial"
        elif is_fixed:
            mode = "fixed"
        else:
            mode = "free"

        copies = 1  # Ensure copies is initialized

        if pdb:
            pdb_path = pdb
            pdb_str = structure2pdb(pdb_path)
            if self.symmetry == "auto":
                a, pdb_str = self.run_ananas(pdb_str)
                if a is None:
                    print("ERROR: no symmetry detected")
                    self.symmetry = None
                    sym, copies = None, 1
                else:
                    if a["group"][0] == "c":
                        self.symmetry = "cyclic"
                        sym, copies = a["group"], int(a["group"][1:])
                    elif a["group"][0] == "d":
                        self.symmetry = "dihedral"
                        sym, copies = a["group"], 2 * int(a["group"][1:])
                    else:
                        print(
                            f'ERROR: the detected symmetry ({a["group"]}) not currently supported'
                        )
                        self.symmetry = None
                        sym, copies = None, 1

            elif mode == "fixed":
                pdb_str = structure2pdb(pdb_path, chains=fixed_chains)

            pdb_filename = f"{self.out_dir}/input.pdb"
            with open(pdb_filename, "w") as handle:
                handle.write(pdb_str)

            parsed_pdb = parse_pdb(pdb_filename)
            self.opts.append(f"inference.input_pdb={pdb_filename}")
            if mode in ["partial"]:
                if self.partial_T == "auto":
                    self.iterations = int(80 * (self.iterations / 200))
                else:
                    self.iterations = int(self.partial_T)
                self.opts.append(f"diffuser.partial_T={self.iterations}")
                contigs = fix_partial_contigs(contigs, parsed_pdb)
            else:
                self.opts.append(f"diffuser.T={self.iterations}")
                contigs = fix_contigs(contigs, parsed_pdb)
        else:
            # Handle the case where pdb is None or empty
            self.opts.append(f"diffuser.T={self.iterations}")
            parsed_pdb = None
            contigs = fix_contigs(contigs, parsed_pdb)

        if self.hotspot is not None and self.hotspot != "":
            hotspot = ",".join(self.hotspot.replace(",", " ").split())
            self.opts.append(f"ppi.hotspot_res='[{hotspot}]'")

        if self.symmetry is not None:
            sym_opts = ["--config-name symmetry", f"inference.symmetry={self.symmetry}"]
            if self.add_potential:
                sym_opts += [
                    "'potentials.guiding_potentials=[\"type:olig_contacts,weight_intra:1,weight_inter:0.1\"]'",
                    "potentials.olig_intra_all=True",
                    "potentials.olig_inter_all=True",
                    "potentials.guide_scale=2",
                    "potentials.guide_decay=quadratic",
                ]
            self.opts = sym_opts + self.opts
            contigs = sum([contigs] * copies, [])  # Use copies variable safely here

        self.opts.append(f"'contigmap.contigs=[{' '.join(contigs)}]'")

        if self.use_beta_model:
            self.opts += [
                f"inference.ckpt_override_path={self.rf_root}/models/Complex_beta_ckpt.pt"
            ]

        print(f"mode:{mode}")
        print(f"output_prefix:{self.out_prefix}")
        print(f"contigs:{contigs}")

        opts_str = " ".join(self.opts)

        cmd = f"export MKL_SERVICE_FORCE_INTEL=1; HYDRA_FULL_ERROR=1 {self.python} {self.rf_root}/scripts/run_inference.py {opts_str}"
        if log_path is not None:
            cmd += f" > {log_path} 2>&1"

        return self.run(cmd, self.iterations)


def get_args():
    parser = argparse.ArgumentParser(description="Run RFdiffusion")
    parser.add_argument("--rf_root", type=str, required=True)
    parser.add_argument("--out_dir", type=str, required=True, help="Output directory")
    parser.add_argument("--contigs", type=str, required=True, help="Contigs to design")
    parser.add_argument("--pdb", type=str, default=None, help="PDB code or path")
    parser.add_argument(
        "--iterations", type=int, default=50, help="Number of iterations"
    )
    parser.add_argument("--symmetry", type=str, default=None, help="Symmetry type")
    parser.add_argument("--order", type=int, default=1, help="Symmetry order")
    parser.add_argument("--hotspot", type=str, default="", help="Hotspot residues")
    parser.add_argument("--chains", type=str, default="", help="Chains to design")
    parser.add_argument("--num_designs", type=int, default=1, help="Number of designs")
    args = parser.parse_args()
    return args


def main(args):
    rf_executor = RFExecutor(
        args.rf_root,
        path=args.out_dir,
        iterations=args.iterations,
        symmetry=args.symmetry,
        order=args.order,
        hotspot=args.hotspot,
        chains=args.chains,
        add_potential=args.add_potential,
        partial_T=args.partial_T,
        num_designs=args.num_designs,
        use_beta_model=args.use_beta_model,
    )
    rf_executor.run_diffusion(args.contigs, args.pdb)


if __name__ == "__main__":
    """
    EXAMPLE:
    python runrf.py   --rf_root '/root/ProtAgent/modelhub/RFdiffusion' \
                      --out_dir './test/tmp' \
                      --contigs '100'
    """
    args = get_args()
    main(args)
