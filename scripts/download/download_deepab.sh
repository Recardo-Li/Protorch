mkdir modelhub
cd modelhub

mkdir DeepAb
cd DeepAb
wget https://data.graylab.jhu.edu/ensemble_abresnet_v1.tar.gz
tar -xf ensemble_abresnet_v1.tar.gz
rm ensemble_abresnet_v1.tar.gz
cd ..