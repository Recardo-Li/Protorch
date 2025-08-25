conda env create -f scripts/create_env/protein_ligand_structure_prediction/umol_environment.yml
conda activate umol

# pip install
# pip install -r scripts/create_env/protein_ligand_structure_prediction/umol_requirements.txt
# pip install --upgrade "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
# pip install --upgrade jax jaxlib==0.4.29+cuda12.cudnn91 -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
# pip install --upgrade numpy

# pip can't find
# conda install -c conda-forge pdbfixer -y
conda install -c conda-forge openmmforcefields