# MMseqs2 API Client: Adjusting Default Timeout Settings

## Overview

This guide provides instructions on how to modify the default timeout and retry configurations for the MMseqs2 API client by locating and editing the `colabfold.py` script.

---

## Step 1: Locate the Configuration File

The relevant settings are located in the `colabfold.py` file, which is typically found within your Python environment's `site-packages` directory. Here are two common methods to find its exact path.

### Method 1: Using Python to Find `site-packages`

This command programmatically finds your `site-packages` directory and searches for `colabfold.py` within it. This is a reliable method that works for most standard Python installations.

```bash
find $(python -c "import site; print(site.getsitepackages()[0])") -name "colabfold.py"
```

### Method 2: Manually Searching a Conda Environment

If you are using a Conda environment (e.g., one named colabfold), you can search within its specific library path.
Note: You must replace /path/to/conda/envs/colabfold/ with the actual path to your Conda installation and environment.
```bash
find /path/to/conda/envs/colabfold/lib/python*/site-packages -name "colabfold.py"
```

## Step 2: Modify the Timeout Settings

### Modifying `run_mmseqs2` in `colabfold.py`  

To adjust the global **timeout** and **retry** configurations:  

1. **Timeout Setting**:  
   - Locate the `request` parameter `timeout=6.02` and modify `6.02` to the desired value.  

2. **Retry Counts**:  
   - Update the condition `error_count > 5` in the following subfunctions:  
     - `submit`  
     - `status`  
     - `download`  
   - Replace `5` with the preferred retry limit.  
