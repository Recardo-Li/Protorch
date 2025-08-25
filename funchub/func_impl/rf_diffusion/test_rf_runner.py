import sys
import os
import json
import argparse
import yaml
from easydict import EasyDict
from rf_executor import RFExecutor

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_path", type=str, required=True)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--symmetry", type=str)
    parser.add_argument("--order", type=str)
    parser.add_argument("--hotspot", type=str)
    parser.add_argument("--chains", type=str)
    parser.add_argument("--add_potential", type=str)
    parser.add_argument("--partial_T", type=str)
    parser.add_argument("--num_designs", type=int)
    parser.add_argument("--use_beta_model", type=str)
    parser.add_argument("--visual", type=str)
    parser.add_argument("--contigs", type=str, default="100")
    parser.add_argument("--pdb", type=str, default="")
    args = parser.parse_args()

    # 配置字典，用于代替 config 文件
    config = EasyDict({
        "output_path": args.output_path,
        "iterations": args.iterations,
        "symmetry": args.symmetry,
        "order": args.order,
        "hotspot": args.hotspot,
        "chains": args.chains,
        "add_potential": args.add_potential,
        "partial_T": args.partial_T,
        "num_designs": args.num_designs,
        "use_beta_model": args.use_beta_model,
        "visual": args.visual,
        "contigs": args.contigs,
        "pdb": args.pdb if args.pdb else ""
    })

    # 设置操作系统环境变量
    print("Setting up OS environment variables")
    for k, v in config.get("setting", {}).get("os_environ", {}).items():
        if v is not None and k not in os.environ:
            os.environ[k] = str(v)
        elif k in os.environ:
            config.setting.os_environ[k] = os.environ[k]

    # 初始化 RFExecutor
    rf_caller = RFExecutor(
        path=config.output_path,
        iterations=config.iterations,
        symmetry=config.symmetry,
        order=config.order,
        hotspot=config.hotspot,
        chains=config.chains,
        add_potential=config.add_potential,
        partial_T=config.partial_T,
        num_designs=config.num_designs,
        use_beta_model=config.use_beta_model,
        visual=config.visual
    )

    # 调用 run_diffusion 方法
    rf_caller.run_diffusion(contigs=config.contigs, pdb=config.pdb)

    sys.exit()