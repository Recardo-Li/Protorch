eval "$(conda shell.bash hook)"

fasta="examples/fasta/umol/7NB4.fasta"
ligand_smiles="CCc1sc2ncnc(N[C@H](Cc3ccccc3)C(=O)O)c2c1-c1cccc(Cl)c1C" #Make sure these are canonical as in RDKit. If you do not have SMILES - you can input a .sdf file to 'make_ligand_feats.py'
num_recycles=3
pos="NONE"
# pos="50,51,53,54,55,56,57,58,59,60,61,62,64,65,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,92,93,94,95,96,97,98,99,100,101,103,104,124,127,128"
id="umol02"
outdir="outputs"

UNICLUST="dataset/Umol/uniclust30_2018_08/uniclust30_2018_08"
HHBLITS="bin/Umol/hh-suite/build/bin/hhblits"
POCKET_PARAMS="modelhub/Umol/params/params_pocket.npy" #Umol-pocket params
NO_POCKET_PARAMS="modelhub/Umol/params/params_no_pocket.npy" #Umol no-pocket params

env_name="umol"

OUTDIR="$outdir/$id"
POCKET_INDICES="$OUTDIR/${id}_pocket_indices.npy" #Zero indexed numpy array of what residues are in the pocket (all CBs within 10Å from the ligand)

for arg in "$@"
do
    case $arg in
        fasta=*) fasta="${arg#*=}" ;;
        ligand_smiles=*) ligand_smiles="${arg#*=}" ;;
        num_recycles=*) num_recycles="${arg#*=}" ;;
        pos=*) pos="${arg#*=}" ;;
        id=*) id="${arg#*=}" ;;
        outdir=*) outdir="${arg#*=}" ;;
        UNICLUST=*) UNICLUST="${arg#*=}" ;;
        HHBLITS=*) HHBLITS="${arg#*=}" ;;
        POCKET_PARAMS=*) POCKET_PARAMS="${arg#*=}" ;;
        NO_POCKET_PARAMS=*) NO_POCKET_PARAMS="${arg#*=}" ;;
        env_name=*) env_name="${arg#*=}" ;;
        *) ;;
    esac
done

conda activate $env_name

mkdir -p $OUTDIR
# Search Uniclust30 with HHblits to generate an MSA (a few minutes)
$HHBLITS -i $fasta -d $UNICLUST -E 0.001 -all -oa3m $OUTDIR/$id'.a3m' -o $OUTDIR/$id'.hhr'

wait
# Generate input feats (seconds)
python3 model/umol/make_msa_seq_feats.py --input_fasta_path $fasta \
                                         --input_msas $OUTDIR/$id'.a3m' \
                                         --outdir $OUTDIR

# SMILES. Alt: --input_sdf 'path_to_input_sdf'
python3 model/umol/make_ligand_feats.py --input_smiles $ligand_smiles \
                                        --outdir $OUTDIR

wait
if [[ $pos != "NONE" ]]; then
    ## Generate a pocket indices file from a list of what residues (zero indexed) are in the pocket (all CBs within 10Å from the ligand). (seconds)
    python3 model/umol/make_targetpost_npy.py --outfile $POCKET_INDICES \
                                              --target_pos $pos
    CKPT=$POCKET_PARAMS
else
    CKPT=$NO_POCKET_PARAMS
    POCKET_INDICES="NONE"
fi

# Predict (a few minutes)
MSA_FEATS=$OUTDIR/msa_features.pkl
LIGAND_FEATS=$OUTDIR/ligand_inp_features.pkl

#Change to no-pocket params if no pocket
#Then also leave out the target pos
python3 model/umol/predict.py --msa_features  $MSA_FEATS \
                              --ligand_features $LIGAND_FEATS \
                              --id $id \
                              --ckpt_params $CKPT \
                              --target_pos $POCKET_INDICES \
                              --num_recycles $num_recycles \
                              --outdir $OUTDIR

wait
RAW_PDB=$OUTDIR/$id'_pred_raw.pdb'
python3 model/umol/relax/align_ligand_conformer.py --pred_pdb $RAW_PDB \
                                                   --ligand_smiles $ligand_smiles \
                                                   --outdir $OUTDIR

grep ATOM $OUTDIR/$id'_pred_raw.pdb' > $OUTDIR/$id'_pred_protein.pdb'
echo "The unrelaxed predicted protein can be found at $OUTDIR/${id}_pred_protein.pdb and the ligand at $OUTDIR/${id}_pred_ligand.sdf"


# Relax the protein (a few minutes)
# This fixes clashes mainly in the protein, but also in the protein-ligand interface.

PRED_PROTEIN=$OUTDIR/$id'_pred_protein.pdb'
PRED_LIGAND=$OUTDIR/$id'_pred_ligand.sdf'
RESTRAINTS="CA+ligand" # or "protein"
python3 model/umol/relax/openmm_relax.py --input_pdb $PRED_PROTEIN \
                                         --ligand_sdf $PRED_LIGAND \
                                         --file_name $id \
                                         --restraint_type $RESTRAINTS \
                                         --outdir $OUTDIR

wait
#Write plDDT to Bfac column
RAW_COMPLEX=$OUTDIR/$id'_pred_raw.pdb'
RELAXED_COMPLEX=$OUTDIR/$id'_relaxed_complex.pdb'
python3 model/umol/relax/add_plddt_to_relaxed.py  --raw_complex $RAW_COMPLEX \
                                                  --relaxed_complex $RELAXED_COMPLEX  \
                                                  --outdir $OUTDIR
echo "The final relaxed structure can be found at $OUTDIR/${id}_relaxed_plddt.pdb"
