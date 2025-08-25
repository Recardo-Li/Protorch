import sys
import os
import shutil
import yaml
import argparse
from pathlib import Path
from enum import IntEnum
from typing import List, Dict, Any, Optional

sys.path.append(".")

DEFAULT_PYTHON_FALLBACK = "/home/public/miniconda3/envs/agent/bin/python"

class ScriptType(IntEnum):
    PYTHON = 0
    SHELL = 1

def detect_script_type(script_path: str) -> ScriptType:
    ext = os.path.splitext(script_path)[1].lower()

    if ext == ".py":
        return ScriptType.PYTHON

    if ext in [".sh", ".bash"]:
        return ScriptType.SHELL

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line.startswith("#!") and "python" in first_line:
                return ScriptType.PYTHON
            if first_line.startswith("#!") and ("bash" in first_line or "sh" in first_line):
                return ScriptType.SHELL
    except Exception:
        pass
    return ScriptType.SHELL

def _safe_name(d: Dict[str, Any], default: str = "param") -> str:
    return str(d.get("name", default))

def _example_input_items(params: List[Dict[str, Any]]) -> str:
    if not params:
        return ""
    items = [f'"{p.get("name", "param")}": None' for p in params]
    return ", ".join(items)

def generate_caller_for_script(toolname: str,
                               script_filename: str,
                               script_type: ScriptType,
                               required_params: List[Dict[str, Any]],
                               optional_params: List[Dict[str, Any]],
                               return_values: List[Dict[str, Any]],
                               return_scores: List[Dict[str, Any]],
                               script_arg_spec: Optional[List[Dict[str, Any]]] = None) -> str:

    required_params = required_params or []
    optional_params = optional_params or []
    return_values = return_values or []
    return_scores = return_scores or []
    script_arg_spec = script_arg_spec or []

    # Build function signature
    func_parts = []

    for p in required_params:
        func_parts.append(_safe_name(p))

    for p in optional_params:
        default = p.get("default", None)

        if default is None or str(default).lower() == "null":
            func_parts.append(f"{_safe_name(p)}=None")
        else:
            func_parts.append(f"{_safe_name(p)}={repr(default)}")
    func_signature = ", ".join(func_parts)

    example_items = _example_input_items(required_params + optional_params)
    class_name = "".join(part.capitalize() for part in str(toolname).split("_") if part)

    # Build script_arg_spec handling for shell scripts
    spec_lines: List[str] = []
    spec_lines.append("        # Build pos_args/flags for the command")
    spec_lines.append("        pos_args = []")

    if not script_arg_spec:
        # Generic fallback (no script_arg_spec): Try to infer executable from top-level config
        spec_lines.append("        # Generic fallback when script_arg_spec is not provided")
        spec_lines.append("        try:")
        spec_lines.append("            exe_rel = None")
        spec_lines.append("            exe_key = None")
        spec_lines.append("            # Inspect top-level keys in config for plausible executable paths")
        spec_lines.append("            # We skip obvious non-exec keys")
        spec_lines.append("            blacklist = set(['document', 'example_output', 'script_arg_spec'])")
        spec_lines.append("            cfg_keys = []")
        spec_lines.append("            try:")
        spec_lines.append("                # EasyDict may behave like dict; try .keys()")
        spec_lines.append("                cfg_keys = list(self.config.keys())")
        spec_lines.append("            except Exception:")
        spec_lines.append("                try:")
        spec_lines.append("                    cfg_keys = list(self.config.__dict__.keys())")
        spec_lines.append("                except Exception:")
        spec_lines.append("                    cfg_keys = []")
        spec_lines.append("            for k in cfg_keys:")
        spec_lines.append("                if k in blacklist:")
        spec_lines.append("                    continue")
        spec_lines.append("                try:")
        spec_lines.append("                    val = self.config.get(k)")
        spec_lines.append("                except Exception:")
        spec_lines.append("                    val = None")
        spec_lines.append("                if isinstance(val, str) and val:")
        spec_lines.append("                    # Heuristics: values starting with 'bin/' or containing '/' or ending with typical exe names")
        spec_lines.append("                    if val.startswith('bin') or '/' in val or val.endswith('.exe') or val.endswith('.sh') or val.endswith('.out'):")
        spec_lines.append("                        exe_rel = val")
        spec_lines.append("                        exe_key = k")
        spec_lines.append("                        break")
        spec_lines.append("        except Exception:")
        spec_lines.append("            exe_rel = None")
        spec_lines.append("")
        spec_lines.append("        # Resolve exe path if found")
        spec_lines.append("        if isinstance(exe_rel, str) and os.path.isabs(exe_rel) and os.path.exists(exe_rel):")
        spec_lines.append("            exe_path = exe_rel")
        spec_lines.append("        elif isinstance(exe_rel, str):")
        spec_lines.append("            exe_path = os.path.join(ROOT_DIR, exe_rel)")
        spec_lines.append("        else:")
        spec_lines.append("            exe_path = exe_rel")
        spec_lines.append("")

        # Resolve input (first required parameter) if exists
        first_req_name = required_params[0]['name'] if required_params else None
        if first_req_name:
            spec_lines.append(f"        input_val = {first_req_name}")
            spec_lines.append("        seq_candidate = None")
            spec_lines.append("        if isinstance(input_val, str) and os.path.isabs(input_val) and os.path.exists(input_val):")
            spec_lines.append("            seq_candidate = input_val")
            spec_lines.append("        elif isinstance(input_val, str) and os.path.exists(input_val):")
            spec_lines.append("            seq_candidate = os.path.abspath(input_val)")
            spec_lines.append("        else:")
            spec_lines.append("            cand = os.path.join(self.out_dir, input_val) if isinstance(input_val, str) else None")
            spec_lines.append("            if cand and os.path.exists(cand):")
            spec_lines.append("                seq_candidate = cand")
            spec_lines.append("            else:")
            spec_lines.append("                cand2 = os.path.join(BASE_DIR, input_val) if isinstance(input_val, str) else None")
            spec_lines.append("                if cand2 and os.path.exists(cand2):")
            spec_lines.append("                    seq_candidate = cand2")
            spec_lines.append("                else:")
            spec_lines.append("                    seq_candidate = input_val")
        else:
            spec_lines.append("        seq_candidate = None")

        spec_lines.append("")
        spec_lines.append("        # Prepare output path under tool-specific output directory")
        spec_lines.append("        now = start.strftime('%Y%m%d_%H%M')")
        spec_lines.append("        base = os.path.splitext(os.path.basename(seq_candidate))[0] if seq_candidate else 'out'")
        spec_lines.append(f"        result_dir = os.path.join(self.out_dir, '{toolname}', now)")
        spec_lines.append("        os.makedirs(result_dir, exist_ok=True)")
        spec_lines.append("        out_path = os.path.join(result_dir, base + '.out')")
        spec_lines.append("")
        spec_lines.append("        # Provide positional args: exe (if found), input, output")
        spec_lines.append("        pos_args.extend([str(exe_path) if exe_path else '', str(seq_candidate) if seq_candidate else '', str(out_path)])")
    else:
        # Build code per-entry in script_arg_spec

        for i, entry in enumerate(script_arg_spec):
            ename = entry.get("name", f"arg{i}")
            source = entry.get("source", "input")
            key = entry.get("key", ename)
            ptype = entry.get("type", "TEXT").upper()
            kind = entry.get("kind", "positional")
            required_flag = bool(entry.get("required", True))
            flag_name = entry.get("flag", None)

            if source == "input":
                lines = []
                lines.append(f"        # script_arg_spec[{i}] from input -> {key}")
                lines.append(f"        val_{ename} = None")
                lines.append("        try:")
                lines.append(f"            val_{ename} = {key}")
                lines.append("        except Exception:")
                lines.append(f"            val_{ename} = None")

                if required_flag:
                    lines.append(f"        if val_{ename} is None:")
                    lines.append(f"            return {{'error': 'Missing required input parameter: {key}'}}")

                if ptype == "PATH":
                    lines.append(f"        if isinstance(val_{ename}, str) and os.path.isabs(val_{ename}) and os.path.exists(val_{ename}):")
                    lines.append(f"            resolved_{ename} = val_{ename}")
                    lines.append(f"        elif isinstance(val_{ename}, str) and os.path.exists(val_{ename}):")
                    lines.append(f"            resolved_{ename} = os.path.abspath(val_{ename})")
                    lines.append(f"        else:")
                    lines.append(f"            cand = os.path.join(self.out_dir, val_{ename}) if isinstance(val_{ename}, str) else None")
                    lines.append(f"            if cand and os.path.exists(cand):")
                    lines.append(f"                resolved_{ename} = cand")
                    lines.append(f"            else:")
                    lines.append(f"                cand2 = os.path.join(BASE_DIR, val_{ename}) if isinstance(val_{ename}, str) else None")
                    lines.append(f"                if cand2 and os.path.exists(cand2):")
                    lines.append(f"                    resolved_{ename} = cand2")
                    lines.append(f"                else:")
                    lines.append(f"                    resolved_{ename} = val_{ename}")
                    value_ref = f"resolved_{ename}"
                else:
                    value_ref = f"val_{ename}"
                if kind == "flag":
                    fl = flag_name or f"--{key}"
                    lines.append(f"        pos_args.extend([{repr(fl)}, str({value_ref})])")
                else:
                    lines.append(f"        pos_args.append(str({value_ref}))")
                spec_lines.append("\n".join(lines))
            elif source in ("config", "bin"):
                lines = []
                lines.append(f"        # script_arg_spec[{i}] from config -> {key}")
                lines.append(f"        val_{ename} = None")
                lines.append("        try:")
                lines.append(f"            val_{ename} = self.config.get('{key}', None)")
                lines.append("        except Exception:")
                lines.append(f"            val_{ename} = None")
                if required_flag:
                    lines.append(f"        if val_{ename} is None:")
                    lines.append(f"            return {{'error': 'Missing required config field: {key}'}}")
                if ptype == "PATH":
                    lines.append(f"        if isinstance(val_{ename}, str) and os.path.isabs(val_{ename}) and os.path.exists(val_{ename}):")
                    lines.append(f"            resolved_{ename} = val_{ename}")
                    lines.append("        else:")
                    lines.append(f"            resolved_{ename} = os.path.join(ROOT_DIR, val_{ename}) if isinstance(val_{ename}, str) else val_{ename}")
                    value_ref = f"resolved_{ename}"
                else:
                    value_ref = f"val_{ename}"
                if kind == "flag":
                    fl = flag_name or f"--{key}"
                    lines.append(f"        pos_args.extend([{repr(fl)}, str({value_ref})])")
                else:
                    lines.append(f"        pos_args.append(str({value_ref}))")
                spec_lines.append("\n".join(lines))
            elif source == "literal":
                val = entry.get("key", "")

                if kind == "flag":
                    fl = flag_name or f"--{key}"
                    spec_lines.append(f"        pos_args.extend([{repr(fl)}, {repr(str(val))}])")
                else:
                    spec_lines.append(f"        pos_args.append({repr(str(val))})")
            elif source == "generated":
                lines = []
                lines.append(f"        # script_arg_spec[{i}] generated -> {ename}")
                lines.append("        now = start.strftime('%Y%m%d_%H%M')")

                if required_params:
                    first_req = required_params[0]['name']
                    lines.append(f"        base_in = os.path.splitext(os.path.basename({first_req} if ({first_req} and isinstance({first_req}, str)) else 'input'))[0] if ({first_req}) else 'out'")
                else:
                    lines.append("        base_in = 'out'")
                lines.append(f"        result_dir = os.path.join(self.out_dir, '{toolname}', now)")
                lines.append("        os.makedirs(result_dir, exist_ok=True)")
                ext = entry.get("ext", None)

                if ext:
                    if not ext.startswith("."):
                        ext = "." + ext
                    lines.append(f"        gen_path = os.path.join(result_dir, base_in + '{ext}')")
                else:
                    lines.append("        gen_path = os.path.join(result_dir, base_in + '.out')")
                if kind == "flag":
                    fl = flag_name or f"--{ename}"
                    lines.append(f"        pos_args.extend([{repr(fl)}, str(gen_path)])")
                else:
                    lines.append(f"        pos_args.append(str(gen_path))")
                spec_lines.append("\n".join(lines))
            else:
                spec_lines.append(f"        # Unknown source '{source}' -> append key as string")
                spec_lines.append(f"        pos_args.append(str({repr(key)}))")

    spec_block = "\n\n".join(spec_lines)

    result_lines: List[str] = []
    result_lines.append("        result = {}")

    if return_values:
        rv0 = return_values[0].get("name", "output")
        result_lines.append(f"        result['{rv0}'] = output")

        for rv in return_values[1:]:
            rn = rv.get("name")
            if rn:
                result_lines.append(f"        result['{rn}'] = None")
    else:
        result_lines.append("        result['output'] = output")
    if any(rs.get("name") == "duration" for rs in (return_scores or [])):
        result_lines.append("        result['duration'] = spend_time")
    result_lines.append("        return result")
    result_block = "\n".join(result_lines)

    # Templates for shell and python caller
    shell_template = """import sys
import os
import subprocess
import datetime

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

@register_tool

class {class_name}(BaseTool):
    def __init__(self, out_dir: str = f"{{ROOT_DIR}}/outputs/{toolname}", **kwargs):
        super().__init__(config_path=os.path.join(BASE_DIR, "config.yaml"), out_dir=out_dir, **kwargs)

        try:
            if isinstance(self.config.document, list) and self.config.document:
                self.config.document = self.config.document[0]
        except Exception:
            pass

    def __call__(self, {func_signature}) -> dict:
        start = datetime.datetime.now()

{spec_block}

        script_path = os.path.join(BASE_DIR, "{script_filename}")

        if not os.path.exists(script_path):
            return {{'error': f"Command script not found: {{script_path}}"}}

        cmd_list = ["bash", script_path] + pos_args

        try:
            with open(self.log_path, "w", encoding="utf-8") as logf:
                proc = subprocess.run(cmd_list, cwd=ROOT_DIR, stdout=logf, stderr=logf, text=True)
                rc = proc.returncode
        except Exception as e:
            try:
                with open(self.log_path, "a", encoding="utf-8") as logf:
                    logf.write("\\nException when running command: " + str(e) + "\\n")
            except Exception:
                pass

            return {{'error': str(e)}}

        spend_time = (datetime.datetime.now() - start).total_seconds()

        if rc != 0:
            try:
                with open(self.log_path, "r", encoding="utf-8") as logf:
                    logtxt = logf.read()
            except Exception:
                logtxt = f"Process exited with code {{rc}}, log unavailable."
            return {{'error': f"Script failed (exit {{rc}}). Log: {{logtxt}}"}}

        try:
            with open(self.log_path, "r", encoding="utf-8") as logf:
                output = logf.read()
        except Exception:
            output = ""

{result_block}

if __name__ == '__main__':
    tool = {class_name}(out_dir=BASE_DIR)
    input_args = {{{example_items}}}
    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs)
"""

    python_param_blocks = []

    for p in required_params + optional_params:
        name = p["name"]
        ptype = p.get("type", "TEXT").upper()
        if ptype == "PATH":
            block = (
                f"        if {name} is not None:\n"
                f"            if not os.path.isabs({name}):\n"
                f"                arg_{name} = os.path.join(self.out_dir, {name})\n"
                f"            else:\n"
                f"                arg_{name} = {name}\n"
                f"            script_args.extend(['--{name}', str(arg_{name})])"
            )
        else:
            block = (
                f"        if {name} is not None:\n"
                f"            script_args.extend(['--{name}', str({name})])"
            )
        python_param_blocks.append(block)
    python_param_block = "\n\n".join(python_param_blocks)

    python_template = """import sys
import os
import datetime
import shlex

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@register_tool

class {class_name}(BaseTool):
    def __init__(self, out_dir: str = f"{{ROOT_DIR}}/outputs/{toolname}", **kwargs):
        super().__init__(config_path=os.path.join(BASE_DIR, "config.yaml"), out_dir=out_dir, **kwargs)

        try:
            if isinstance(self.config.document, list) and self.config.document:
                self.config.document = self.config.document[0]
        except Exception:
            pass

    def __call__(self, {func_signature}) -> dict:
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        os.makedirs(os.path.join(self.out_dir, "{toolname}", now), exist_ok=True)

        script_path = os.path.join(BASE_DIR, "{script_filename}")

        if not os.path.exists(script_path):
            return {{'error': f"Command script not found: {{script_path}}"}}

        # Build command arguments (flags)
        script_args = []

{param_block}

        python_exec = None

        try:
            python_exec = self.config.get('python', None)
        except Exception:
            python_exec = None

        if not python_exec:
            python_exec = sys.executable if sys.executable else "{fallback}"

        cmd_list = [python_exec, script_path] + script_args
        cmd_str = " ".join(shlex.quote(x) for x in cmd_list)
        cmd_str += f" > {{self.log_path}} 2>&1"

        try:
            os.system(cmd_str)
        except Exception as e:
            return {{'error': str(e)}}

        spend_time = (datetime.datetime.now() - start).total_seconds()

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                output = f.read()
        except Exception:
            output = ""

{result_block}

if __name__ == '__main__':
    tool = {class_name}(out_dir=BASE_DIR)
    input_args = {{{example_items}}}
    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs)
"""
    # Choose template
    if script_type == ScriptType.SHELL:
        tpl = shell_template.format(
            class_name=class_name,
            toolname=toolname,
            script_filename=script_filename,
            func_signature=func_signature,
            spec_block=spec_block,
            result_block=result_block,
            example_items=example_items
        )
    else:
        tpl = python_template.format(
            class_name=class_name,
            toolname=toolname,
            script_filename=script_filename,
            func_signature=func_signature,
            param_block=python_param_block,
            result_block=result_block,
            example_items=example_items,
            fallback=DEFAULT_PYTHON_FALLBACK
        )
    return tpl

def validate_document(doc: Any) -> (bool, Optional[str]):
    if not isinstance(doc, dict):
        return False, "document must be a mapping"

    if "tool_name" not in doc:
        return False, "document.tool_name missing"
    doc.setdefault("required_parameters", [])
    doc.setdefault("optional_parameters", [])
    doc.setdefault("return_values", [])
    doc.setdefault("return_scores", [])
    return True, None

def create_tool_from_files(command_path: str, config_path: str, overwrite: bool = False) -> None:
    if not os.path.exists(command_path):
        raise FileNotFoundError(f"Script not found: {command_path}")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    doc = cfg.get("document")

    if isinstance(doc, list) and doc:
        doc = doc[0]

    if not isinstance(doc, dict):
        raise TypeError("Invalid 'document' in config.yaml")

    ok, reason = validate_document(doc)

    if not ok:
        raise ValueError(f"Invalid document: {reason}")

    toolname = str(doc["tool_name"]).lower().replace(" ", "_")
    tool_dir = os.path.join("agent", "tools", toolname)

    if os.path.exists(tool_dir):
        if not overwrite:
            ans = input(f"Tool dir {tool_dir} exists. Overwrite? (y/N): ").strip().lower()
            if ans != "y":
                print("Aborted.")
                return
        shutil.rmtree(tool_dir)

    os.makedirs(tool_dir, exist_ok=True)

    script_filename = os.path.basename(command_path)

    shutil.copy2(command_path, os.path.join(tool_dir, script_filename))
    shutil.copy2(config_path, os.path.join(tool_dir, "config.yaml"))

    script_type = detect_script_type(command_path)

    script_arg_spec = cfg.get("script_arg_spec", None)

    caller_content = generate_caller_for_script(
        toolname=toolname,
        script_filename=script_filename,
        script_type=script_type,
        required_params=doc.get("required_parameters", []),
        optional_params=doc.get("optional_parameters", []),
        return_values=doc.get("return_values", []),
        return_scores=doc.get("return_scores", []),
        script_arg_spec=script_arg_spec
    )

    caller_path = os.path.join(tool_dir, "caller.py")
    with open(caller_path, "w", encoding="utf-8") as fw:
        fw.write(caller_content)

    print(f"Tool {toolname} created in {tool_dir}")
    print(f"  - {os.path.join(tool_dir, script_filename)}")
    print(f"  - {os.path.join(tool_dir, 'config.yaml')}")
    print(f"  - {caller_path}")

def _parse_args():
    p = argparse.ArgumentParser(description="Create tool from script and config")
    p.add_argument("--command", "-c", help="Path to command script (py or sh)")
    p.add_argument("--config", "-f", help="Path to config.yaml")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing tool dir")
    return p.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    if not args.command:
        args.command = input("Enter full path to script: ").strip()
    if not args.config:
        args.config = input("Enter full path to config.yaml: ").strip()

    try:
        create_tool_from_files(args.command, args.config, overwrite=args.overwrite)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)