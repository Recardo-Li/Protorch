cd /zhouyuyang/project/ProtAgent
CUDA_VISIBLE_DEVICES=0,1
LOCAL_RANK=0
WORLD_SIZE=2
python scripts/train.py \
    config/uniprot.yaml