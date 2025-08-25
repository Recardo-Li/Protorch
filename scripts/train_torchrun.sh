cd /zhouyuyang/project/ProtAgent
CUDA_VISIBLE_DEVICES=0,1
LOCAL_RANK=0
WORLD_SIZE=2
/zhouyuyang/env/miniconda3/envs/toolkenGPT/bin/python -m torch.distributed.run \
    --nproc_per_node 2 \
    --master_port 1200 \
    scripts/train.py \
    config/train_uniprot.yaml