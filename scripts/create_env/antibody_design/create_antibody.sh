# create and activate new env
conda create -n antibody python=3.8 --yes
conda activate antibody

# pip installpytorchba
pip install -r scripts/create_env/antibody_design/antibody_requirements.txt

# conda install
conda install -c bioconda abnumber --yes
conda install pytorch==1.12.1 torchvision==0.13.1 torchaudio==0.12.1 cudatoolkit=11.6 -c pytorch -c conda-forge --yes

# install pyrosetta
python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta()'

# install libfftw3
apt-get install libfftw3-dev