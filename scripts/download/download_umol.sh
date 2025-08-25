mkdir modelhub
cd modelhub

mkdir Umol
cd Umol
## Get network parameters for Umol (a few minutes)
#Pocket params
wget https://zenodo.org/records/10397462/files/params40000.npy
mkdir params
mv params40000.npy  params/params_pocket.npy
#No-pocket params
wget https://zenodo.org/records/10489242/files/params60000.npy
mv params60000.npy  params/params_no_pocket.npy
cd ../..

wait
mkdir dataset
cd dataset

mkdir Umol
cd Umol
## Get Uniclust30 (10-20 minutes depending on bandwidth)
# 25 Gb download, 87 Gb extracted
wget http://wwwuser.gwdg.de/~compbiol/uniclust/2018_08/uniclust30_2018_08_hhsuite.tar.gz --no-check-certificate
# mkdir uniclust30
# mv uniclust30_2018_08_hhsuite.tar.gz data
tar -zxvf uniclust30_2018_08_hhsuite.tar.gz
cd ../..


wait
mkdir bin
cd bin

mkdir Umol
cd Umol
apt update
apt install cmake
## Install HHblits (a few minutes)
git clone https://github.com/soedinglab/hh-suite.git
mkdir -p hh-suite/build && cd hh-suite/build
cmake -DCMAKE_INSTALL_PREFIX=. ..
make -j 4 && make install
cd ../..

cd ..