import os
import torch
import argparse

from transformers import AutoTokenizer, EsmForProteinFolding
from transformers.models.esm.openfold_utils.protein import to_pdb, Protein as OFProtein
from transformers.models.esm.openfold_utils.feats import atom14_to_atom37


torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

def load_model(model_path, device):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = EsmForProteinFolding.from_pretrained(model_path, device_map=device)
    model.esm = model.esm.half()
    model.trunk.set_chunk_size(64)
    
    return tokenizer, model


def predict(seq, tokenizer, model, save_path=None):
    tokenized_input = tokenizer([seq], return_tensors="pt", add_special_tokens=False)['input_ids']
    tokenized_input = tokenized_input.to(model.device)
    with torch.no_grad():
        output = model(tokenized_input)
    
    if save_path is not None:
        pdb = convert_outputs_to_pdb(output)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w") as w:
            w.write("".join(pdb))
    
    return output


def convert_outputs_to_pdb(outputs):
    final_atom_positions = atom14_to_atom37(outputs["positions"][-1], outputs)
    outputs = {k: v.to("cpu").numpy() for k, v in outputs.items()}
    final_atom_positions = final_atom_positions.cpu().numpy()
    final_atom_mask = outputs["atom37_atom_exists"]
    pdbs = []
    outputs["plddt"] *= 100
    
    for i in range(outputs["aatype"].shape[0]):
        aa = outputs["aatype"][i]
        pred_pos = final_atom_positions[i]
        mask = final_atom_mask[i]
        resid = outputs["residue_index"][i] + 1
        pred = OFProtein(
            aatype=aa,
            atom_positions=pred_pos,
            atom_mask=mask,
            residue_index=resid,
            b_factors=outputs["plddt"][i],
            chain_index=outputs["chain_index"][i] if "chain_index" in outputs else None,
        )
        pdbs.append(to_pdb(pred))
    return pdbs


def main():
    # Load ESMFold
    tokenizer, model = load_model(args.model_path, args.device)
    predict(args.sequence, tokenizer, model, save_path=args.save_path)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--sequence', type=str, required=True, help='Protein sequence'
    )
    parser.add_argument(
        '--model_path', type=str, required=True, help='Path to the ESMFold model'
    )
    parser.add_argument(
        '--save_path', type=str, required=True, help='Path to save the predicted structure'
    )
    parser.add_argument(
        '--device', type=str, default='cuda:0', help='Device to run the model. Default: cuda:0'
    )
    
    return parser.parse_args()


if __name__ == '__main__':
    """
    EXAMPLE:
    python cmd.py   --sequence "AAAAAAA" \
                    --model_path "/home/public/modelhub/esmfold_v1" \
                    --save_path "/root/temp/predicted_structure.pdb" \
                    --device "cuda:1"
    """
    args = get_args()
    main()
    
