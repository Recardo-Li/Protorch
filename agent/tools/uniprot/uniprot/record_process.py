import torch
import json
import random
import os
import re

def record2text(record: list, template: dict, template_id: int = None) -> str or list:
    """
    Convert a record into a text based on the subsection type
    Args:
        record: A list of record containing the following information
        ["uniprot_id", "seq_len", "section", "subsection", "evidences", "text", "note"]

        template: A dictionary of templates for each subsection type

        template_id: An integer indicating which template to use. If None, it will randomly select a template.

    Returns:
        when subsection is not "Taxonomic lineage":
            text (str): a text converted from a record
            raw_text_list (list): a list of raw texts if any
        when subsection is "Taxonomic lineage":
            text (list): a list of texts converted from a record
            raw_text_list (list of lists): a list of lists of raw texts if any
    """

    global raw_text, ori, mut, st, ed, pos, cls, st_aa, ed_aa
    sequence_name, aa_length, section, subsection, evidences, raw_text, note = record
    text = None
    sep = "|"
    raw_text_list = []

    def fill_template(template, template_id, extra_key=None):
        candidates = template[subsection] if extra_key is None else template[subsection][extra_key]

        if template_id is None:
            template_id = random.randint(0, len(candidates) - 1)

        raw_text_list = [eval('f"'+str(item)+'"') for item in re.findall(r'(\{.*?\})', candidates[template_id])]
        return eval('f"' + candidates[template_id] + '"'), raw_text_list

    # Section: Function. Subsection: Function
    if subsection == "Function":
        text = raw_text

    # Section: Function. Subsection: Miscellaneous
    if subsection == "Miscellaneous":
        text = raw_text

    # Section: Function. Subsection: Caution
    if subsection == "Caution":
        text = raw_text

    # Section: Function. Subsection: Catalytic activity
    if subsection == "Catalytic activity":
        text, raw_text_list = fill_template(template, template_id)

        physiologicalReactions = note.split(sep)[-1]
        if physiologicalReactions != "None":
            if physiologicalReactions == "left-to-right":
                plus = "This reaction proceeds in the forward direction."
            else:
                plus = "This reaction proceeds in the reverse direction."

            text = text + " " + plus

    # Section: Function. Subsection: Cofactor
    if subsection == "Cofactor":
        if note == "note":
            text = raw_text
        else:
            text, raw_text_list = fill_template(template, template_id)

    # Section: Function. Subsection: Activity regulation
    if subsection == "Activity regulation":
        text = raw_text

    # Section: Function. Subsection: Biophysicochemical properties
    if subsection == "Biophysicochemical properties":
        text = raw_text

    # Section: Function. Subsection: Pathway
    if subsection == "Pathway":
        text, raw_text_list = fill_template(template, template_id)

    # Section: Function. Subsection: Active site
    if subsection == "Active site":
        pos = note.split(sep)[1]
        if raw_text == "":
            raw_text = "unknown"
        text, raw_text_list = fill_template(template, template_id)
        
    # Section: Function. Subsection: Binding site
    if subsection == "Binding site":
        segments = raw_text.split(sep)
        _, desc, _, ligand, _, ligand_note, _, label, _, part = segments
        raw_text = ligand
        if label != "None":
            raw_text = raw_text + " " + label

        if part != "None":
            raw_text = f"{part} of {raw_text}"

        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: Function. Subsection: Site
    if subsection == "Site":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        # Lowercase the first letter of the raw_text
        raw_text = raw_text[0].lower() + raw_text[1:]
        text, raw_text_list = fill_template(template, template_id)

    # Section: Function. Subsection: DNA binding
    if subsection == "DNA binding":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        if raw_text == "":
            raw_text = "unknown"

        # Lowercase the first letter of the raw_text
        raw_text = raw_text[0].lower() + raw_text[1:]
        text, raw_text_list = fill_template(template, template_id)

    # Section: Function. Subsection: Biotechnology
    if subsection == "Biotechnology":
        text = raw_text

    # Section: Function. Subsection: GO annotation
    if subsection == "GO annotation":
        cls = note.split(sep)[0].lower()
        text, raw_text_list = fill_template(template, template_id)

    # Section: Names and Taxonomy. Subsection: Protein names
    if subsection == "Protein names":
        text, raw_text_list = fill_template(template, template_id)

    # Section: Names and Taxonomy. Subsection: Gene names
    if subsection == "Gene names":
        if note == "orfNames" or note == "orderedLocusNames":
            text, raw_text_list = fill_template(template, template_id, note)
        else:
            text, raw_text_list = fill_template(template, template_id, "normal")

    # Section: Names and Taxonomy. Subsection: Organism
    if subsection == "Organism":
        text, raw_text_list = fill_template(template, template_id)

    # Section: Names and Taxonomy. Subsection: Taxonomic lineage
    if subsection == "Taxonomic lineage":
        classes = raw_text.split("->")
        text = []
        raw_text_list = []
        for raw_text in classes:
            _text, _raw_text_list = fill_template(template, template_id)
            text.append(_text)
            raw_text_list.append(_raw_text_list)

    # Section: Names and Taxonomy. Subsection: Proteomes
    if subsection == "Proteomes":
        text, raw_text_list = fill_template(template, template_id)

    # Section: Names and Taxonomy. Subsection: Virus host
    if subsection == "Virus host":
        _, scientificName, _, commonName, _, synonyms = note.split(sep)
        text = []
        raw_text_list = []
        for raw_text in [scientificName, commonName, synonyms]:
            if raw_text != "None":
                _text, _raw_text_list = fill_template(template, template_id)
                text.append(_text)
                raw_text_list.append(_raw_text_list)
        

    # Section: Disease and Variants. Subsection: Involvement in disease
    if subsection == "Involvement in disease":
        text, raw_text_list = fill_template(template, template_id)

    # Section: Disease and Variants. Subsection: Natural variant
    if subsection == "Natural variant":
        _, pos, _, ori, _, mut = note.split(sep)

        # Lowercase the first letter of the raw_text
        raw_text = raw_text[0].lower() + raw_text[1:] if raw_text != "" else ""
        if raw_text == "":
            text, raw_text_list = fill_template(template, template_id, extra_key="without raw_text")
        else:
            text, raw_text_list = fill_template(template, template_id, extra_key="with raw_text")

    # Section: Disease and Variants. Subsection: Allergenic properties
    if subsection == "Allergenic properties":
        text = raw_text

    # Section: Disease and Variants. Subsection: Toxic dose
    if subsection == "Toxic dose":
        text = raw_text

    # Section: Disease and Variants. Subsection: Pharmaceutical use
    if subsection == "Pharmaceutical use":
        text = raw_text

    # Section: Disease and Variants. Subsection: Disruption phenotype
    if subsection == "Disruption phenotype":
        text = raw_text

    # Section: Disease and Variants. Subsection: Mutagenesis
    if subsection == "Mutagenesis":
        _, st, _, ed, _, ori, _, mut = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        # Lowercase the first letter of the raw_text
        raw_text = raw_text[0].lower() + raw_text[1:]
        text, raw_text_list = fill_template(template, template_id)

    # Section: Subcellular location. Subsection: Subcellular location
    if subsection == "Subcellular location":
        if note == "note":
            text = raw_text
        else:
            text, raw_text_list = fill_template(template, template_id)

    # Section: Subcellular location. Subsection: Transmembrane
    if subsection == "Transmembrane":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"
        if raw_text == "":
            text, raw_text_list = fill_template(template, template_id, extra_key="without raw_text")
        else:
            text, raw_text_list = fill_template(template, template_id, extra_key="with raw_text")

    # Section: Subcellular location. Subsection: Topological domain
    if subsection == "Topological domain":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: Subcellular location. Subsection: Intramembrane
    if subsection == "Intramembrane":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        if raw_text == "":
            text, raw_text_list = fill_template(template, template_id, extra_key="without raw_text")
        else:
            text, raw_text_list = fill_template(template, template_id, extra_key="with raw_text")

    # Section: PTM/Processing. Subsection: Signal peptide
    if subsection == "Signal peptide":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Propeptide
    if subsection == "Propeptide":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"
        if raw_text == "":
            text, raw_text_list = fill_template(template, template_id, extra_key="without raw_text")
        else:
            text, raw_text_list = fill_template(template, template_id, extra_key="with raw_text")

    # Section: PTM/Processing. Subsection: Transit peptide
    if subsection == "Transit peptide":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Chain
    if subsection == "Chain":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Peptide
    if subsection == "Peptide":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Modified residue
    if subsection == "Modified residue":
        _, st, _, ed, _, _ = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Lipidation
    if subsection == "Lipidation":
        _, st, _, ed, _, _ = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Glycosylation
    if subsection == "Glycosylation":
        _, st, _, ed, _, _ = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Disulfide bond
    if subsection == "Disulfide bond":
        _, st, _, ed, _, _, _, _ = note.split(sep)
        text, raw_text_list = fill_template(template, template_id)

    # Section: PTM/Processing. Subsection: Cross-link
    if subsection == "Cross-link":
        _, st, _, ed, _, st_aa, _, ed_aa = note.split(sep)
        if st == ed:
            text, raw_text_list = fill_template(template, template_id, "interchain")
        else:
            text, raw_text_list = fill_template(template, template_id, "intrachain")

    # Section: PTM/Processing. Subsection: Post-translational modification
    if subsection == "Post-translational modification":
        text = raw_text

    # Section: Expression. Subsection: Tissue specificity
    if subsection == "Tissue specificity":
        text = raw_text

    # Section: Expression. Subsection: Developmental stage
    if subsection == "Developmental stage":
        text = raw_text

    # Section: Expression. Subsection: Induction
    if subsection == "Induction":
        text = raw_text

    # Section: Interaction. Subsection: Subunit
    if subsection == "Subunit":
        text = raw_text

    # Section: Family and Domains. Subsection: Domain
    if subsection == "Domain":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: Family and Domains. Subsection: Repeat
    if subsection == "Repeat":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"
        
        

        if raw_text == "":
            raw_text = "not specified"
        text, raw_text_list = fill_template(template, template_id)

    # Section: Family and Domains. Subsection: Compositional bias
    if subsection == "Compositional bias":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: Family and Domains. Subsection: Region
    if subsection == "Region":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"
        text, raw_text_list = fill_template(template, template_id)

    # Section: Family and Domains. Subsection: Coiled coil
    if subsection == "Coiled coil":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: Family and Domains. Subsection: Motif
    if subsection == "Motif":
        _, st, _, ed = note.split(sep)
        if st == ed:
            pos = st
        else:
            pos = f"{st} to {ed}"

        text, raw_text_list = fill_template(template, template_id)

    # Section: Family and Domains. Subsection: Domain (non-positional annotation)
    if subsection == "Domain (non-positional annotation)":
        text = raw_text

    # Section: Family and Domains. Subsection: Sequence similarities
    if subsection == "Sequence similarities":
        text = raw_text

    # Section: Sequence. Subsection: RNA Editing
    if subsection == "RNA Editing":
        if note == "note":
            text = raw_text
        else:
            pos = note.split(sep)[-1]
            text, raw_text_list = fill_template(template, template_id)

    # Section: Sequence. Subsection: Polymorphism
    if subsection == "Polymorphism":
        text = raw_text

    assert text is not None
    return text, raw_text_list

def record2question(record: list, template: dict, template_id: int = None) -> str or list:

    global raw_text, ori, mut, st, ed, pos, cls, st_aa, ed_aa
    sequence_name, aa_length, section, subsection, evidences, raw_text, note = record
    text = None
    sep = "|"

    def fill_template(template, template_id, extra_key=None):
        candidates = template[subsection] if extra_key is None else template[subsection][extra_key]
        if template_id is None:
            template_id = random.randint(0, len(candidates) - 1)

        return eval('f"' + candidates[template_id] + '"')

    if subsection == "Biophysicochemical properties":
        question = fill_template(template, template_id, extra_key=note)
    else:
        question = fill_template(template, template_id)
    assert question is not None
    return question