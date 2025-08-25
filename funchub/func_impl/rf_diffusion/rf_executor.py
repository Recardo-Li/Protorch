import os
import time
import json
import numpy as np
import matplotlib.pyplot as plt
import signal
import sys, random, string, re
import data.globalvar as globalvar
import subprocess
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from agent.action.config import get_temp_dir
from rfdiffusion.inference.utils import parse_pdb
from colabdesign.rf.utils import fix_contigs, fix_partial_contigs, fix_pdb, sym_it
from colabdesign.shared.protein import pdb_to_string

from demo.utils.make_html import make_html
from utils.visualize import visualize

class RFExecutor:
    def __init__(self, path, iterations=50, symmetry="none", order=1, hotspot=None,
                 chains=None, add_potential=False, partial_T="auto",
                 num_designs=1, use_beta_model=False, visual="none"):
        self.out_dir = path
        self.out_prefix = f"{path}/design"
        self.iterations = iterations
        self.symmetry = symmetry
        self.order = order
        self.hotspot = hotspot
        self.chains = chains
        self.add_potential = add_potential
        self.partial_T = partial_T
        self.num_designs = num_designs
        self.use_beta_model = use_beta_model
        self.visual = visual
        os.makedirs(self.out_dir, exist_ok=True)
        self.opts = [f"inference.output_prefix={self.out_prefix}",
                     f"inference.num_designs={num_designs}"]

    def get_pdb(self, pdb_code=None):
        if pdb_code is None or pdb_code == "":
            raise Exception("No PDB code provided")
        elif os.path.isfile(pdb_code):
            return pdb_code
        elif len(pdb_code) == 4:
            if not os.path.isfile(f"{self.out_dir}/{pdb_code}.pdb"):
                os.system(f"wget -P {self.out_dir} -qnc https://files.rcsb.org/download/{pdb_code}.pdb.gz")
                os.system(f"gunzip {self.out_dir}/{pdb_code}.pdb.gz")
            return f"{self.out_dir}/{pdb_code}.pdb"
        else:
            os.system(f"wget -qnc https://alphafold.ebi.ac.uk/files/AF-{pdb_code}-F1-model_v3.pdb")
            return f"{self.out_dir}/AF-{pdb_code}-F1-model_v3.pdb"

    def run_ananas(self, pdb_str):
        pdb_filename = f"{self.out_dir}/ananas_input.pdb"
        out_filename = f"{self.out_dir}/ananas.json"
        with open(pdb_filename, "w") as handle:
            handle.write(pdb_str)

        cmd = f"./ananas {pdb_filename} -u -j {out_filename}"
        if self.symmetry is None:
            os.system(cmd)
        else:
            os.system(f"{cmd} {self.symmetry}")

        try:
            out = json.loads(open(out_filename, "r").read())
            results, AU = out[0], out[-1]["AU"]
            group = AU["group"]
            chains = AU["chain names"]
            rmsd = results["Average_RMSD"]
            print(f"AnAnaS detected {group} symmetry at RMSD:{rmsd:.3}")

            C = np.array(results['transforms'][0]['CENTER'])
            A = [np.array(t["AXIS"]) for t in results['transforms']]

            new_lines = []
            for line in pdb_str.split("\n"):
                if line.startswith("ATOM"):
                    chain = line[21:22]
                    if chain in chains:
                        x = np.array([float(line[i:(i+8)]) for i in [30, 38, 46]])
                        if group[0] == "c":
                            x = sym_it(x, C, A[0])
                        if group[0] == "d":
                            x = sym_it(x, C, A[1], A[0])
                        coord_str = "".join(["{:8.3f}".format(a) for a in x])
                        new_lines.append(line[:30] + coord_str + line[54:])
                else:
                    new_lines.append(line)
            return results, "\n".join(new_lines)

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, pdb_str

    def run_command_and_get_pid(self, command, logger):
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Running command: {command}")

        # 创建一个单独的线程来处理输出，以避免阻塞
        def log_output(pipe, log_func):
            for line in iter(pipe.readline, b''):  # 逐行读取
                log_func(line.decode('utf-8').strip())  # 解码并去除末尾的换行符
            pipe.close()

        # 启动线程来处理标准输出
        from threading import Thread
        stdout_thread = Thread(target=log_output, args=(process.stdout, logger.info))
        stderr_thread = Thread(target=log_output, args=(process.stderr, logger.error))

        stdout_thread.start()
        stderr_thread.start()

        # 等待子进程执行完毕
        process.wait()  # 这会阻塞，直到子进程完成

        # 确保所有输出线程结束
        stdout_thread.join()
        stderr_thread.join()

        # 返回进程对象
        
        return process

    def is_process_running(self, process):
        return process.poll() is None

    def run(self, command, steps, logger, num_designs=1):
        """
        Runs a command with progress tracking for designs and steps.

        Args:
            command (str): The command to execute.
            steps (int): The number of steps in each design.
            logger (object): Logger for logging output.
            num_designs (int): Number of designs to run. Defaults to 1.
        """
        print("Steps =", steps)
        process = self.run_command_and_get_pid(command, logger)  # Start subprocess and get process handle

        try:
            fail = False
            with logging_redirect_tqdm(loggers=[logger]):
                for design_idx in tqdm(range(num_designs), desc="Designs", unit="design", leave=True):
                    for step in tqdm(range(steps), desc="Steps", unit="step", leave=False):
                        wait = True
                        while wait and not fail:
                            time.sleep(0.1)
                            pdb_file = f"/dev/shm/{step}.pdb"
                            if os.path.isfile(pdb_file):
                                with open(pdb_file, 'r') as file:
                                    pdb_str = file.read()
                                if pdb_str.endswith("TER"):
                                    wait = False
                                elif not self.is_process_running(process):
                                    fail = True
                            elif not self.is_process_running(process):
                                fail = True

                        if fail:
                            logger.error(f"Process failed during design {design_idx + 1}, step {step + 1}.")
                            break  # Exit inner loop if process fails

                    if fail:
                        logger.error("Aborting remaining designs due to failure.")
                        break  # Exit outer loop if process fails

        except KeyboardInterrupt:
            logger.warning("Process interrupted by user.")
            if process:
                process.terminate()

        finally:
            if self.is_process_running(process):
                process.terminate()
            logger.info("Run completed.")
            
            if fail:
                return {
                    "status": "failure",
                    "result": None
                }
            else:
                output_path = f"{self.out_prefix}_0.pdb"
                return {
                    "status": "success",
                    "result": output_path,
                    "filedownload": output_path
                }

    def run_diffusion(self, contigs, pdb, logger):
        contigs = contigs.replace(",", " ").replace(":", " ").split()
        is_fixed, is_free = False, False
        fixed_chains = []
        for contig in contigs:
            for x in contig.split("/"):
                a = x.split("-")[0]
                if a[0].isalpha():
                    is_fixed = True
                    if a[0] not in fixed_chains:
                        fixed_chains.append(a[0])
                if a.isnumeric():
                    is_free = True
        if len(contigs) == 0 or not is_free:
            mode = "partial"
        elif is_fixed:
            mode = "fixed"
        else:
            mode = "free"

        copies = 1  # Ensure copies is initialized

        if pdb:
            pdb_str = pdb_to_string(self.get_pdb(pdb), chains=self.chains)
            if self.symmetry == "auto":
                a, pdb_str = self.run_ananas(pdb_str)
                if a is None:
                    print('ERROR: no symmetry detected')
                    self.symmetry = None
                    sym, copies = None, 1
                else:
                    if a["group"][0] == "c":
                        self.symmetry = "cyclic"
                        sym, copies = a["group"], int(a["group"][1:])
                    elif a["group"][0] == "d":
                        self.symmetry = "dihedral"
                        sym, copies = a["group"], 2 * int(a["group"][1:])
                    else:
                        print(f'ERROR: the detected symmetry ({a["group"]}) not currently supported')
                        self.symmetry = None
                        sym, copies = None, 1

            elif mode == "fixed":
                pdb_str = pdb_to_string(pdb_str, chains=fixed_chains)

            pdb_filename = f"{self.out_dir}/input.pdb"
            with open(pdb_filename, "w") as handle:
                handle.write(pdb_str)

            parsed_pdb = parse_pdb(pdb_filename)
            self.opts.append(f"inference.input_pdb={pdb_filename}")
            if mode in ["partial"]:
                if self.partial_T == "auto":
                    self.iterations = int(80 * (self.iterations / 200))
                else:
                    self.iterations = int(self.partial_T)
                self.opts.append(f"diffuser.partial_T={self.iterations}")
                contigs = fix_partial_contigs(contigs, parsed_pdb)
            else:
                self.opts.append(f"diffuser.T={self.iterations}")
                contigs = fix_contigs(contigs, parsed_pdb)
        else:
            # Handle the case where pdb is None or empty
            self.opts.append(f"diffuser.T={self.iterations}")
            parsed_pdb = None
            contigs = fix_contigs(contigs, parsed_pdb)

        if self.hotspot is not None and self.hotspot != "":
            hotspot = ",".join(self.hotspot.replace(",", " ").split())
            self.opts.append(f"ppi.hotspot_res='[{hotspot}]'")

        if self.symmetry is not None:
            sym_opts = ["--config-name symmetry", f"inference.symmetry={self.symmetry}"]
            if self.add_potential:
                sym_opts += ["'potentials.guiding_potentials=[\"type:olig_contacts,weight_intra:1,weight_inter:0.1\"]'",
                             "potentials.olig_intra_all=True", "potentials.olig_inter_all=True",
                             "potentials.guide_scale=2", "potentials.guide_decay=quadratic"]
            self.opts = sym_opts + self.opts
            contigs = sum([contigs] * copies, [])  # Use copies variable safely here

        self.opts.append(f"'contigmap.contigs=[{' '.join(contigs)}]'")
        # self.opts += ["inference.dump_pdb=True", "inference.dump_pdb_path='/dev/shm'"]
        
        modelhub_root = globalvar.modelhub_root
        rf_root = f"{modelhub_root}/RFdiffusion"
        
        if self.use_beta_model:
            self.opts += [f"inference.ckpt_override_path={rf_root}/models/Complex_beta_ckpt.pt"]

        logger.info(f"mode:{mode}")
        logger.info(f"output_prefix:{self.out_prefix}")
        logger.info(f"contigs:{contigs}")

        opts_str = " ".join(self.opts)
        
        cmd = f"HYDRA_FULL_ERROR=1 {rf_root}/scripts/run_inference.py {opts_str}"

        return self.run(cmd, self.iterations, logger)
    

# # 初始化 RFCaller 实例
# rf_caller = RFCaller(
#     path="../../../../test",                # 名称
#     iterations=50,              # 迭代次数
#     symmetry="None",            # 对称性设置
#     order=1,                    # 对称性阶数
#     hotspot="",                 # 热点（如果没有指定）
#     chains="",                  # 链（没有指定）
#     add_potential=True,         # 启用 add_potential
#     partial_T="auto",           # 部分扩散步骤设置为自动
#     num_designs=1,              # 设计数量
#     use_beta_model=False,       # 不使用 beta 模型
#     visual="image"              # 可视化类型为图像
# )
#
# # 调用 run_diffusion 方法
# rf_caller.run_diffusion(contigs="100", pdb="")

