# Virtual Environment Auto-Setup

This document explains how CTCC automatically sets up virtual environments for fresh clones.

## Problem Statement

When a colleague clones the CTCC repository:
- `venv/` is not in git (ignored by `.gitignore`)
- Without it, calculations fail with "ModuleNotFoundError"
- Manual setup is error-prone and time-consuming

## Solution

All CTCC entry points now **automatically** check for and set up the correct virtual environment with all dependencies.

## What Gets Auto-Setup

### CLI Commands (all .command files)
When you run any of these:
- `run_yaml_csv.command`
- `run_json_csv.command`
- `run_json_json.command`

They automatically:
1. Check if `venv/` exists, create if missing
2. Install dependencies from `requirements.txt` (pyyaml, pandas, numpy, fastapi, uvicorn, etc.)
3. Run calculations using the venv Python

### API Server
When you run:
- `server/run_calc_server.command` or `run_calc_server.command` (from repo root)

The script activates the **same root venv** (`venv/`), installs from root `requirements.txt`, then runs uvicorn from the server directory. The server runs `ctcc.py` in a subprocess using the same Python (`sys.executable`), so one venv serves both CLI and API.

## Fresh Clone Workflow

After cloning the repo, colleagues can immediately:

```bash
# Start the API server - everything auto-installs
cd server
./run_calc_server.command

# OR run CLI calculations - everything auto-installs
./run_json_json.command
```

No manual venv setup required!

## Technical Details

### Single environment

One virtual environment at **repo root** (`venv/`) is used by both the CLI and the API server:

- **Location:** `CTCC/venv/` (repo root, i.e. the directory containing `ctcc.py` and `server/`)
- **Dependencies:** One `requirements.txt` at repo root (pyyaml, pandas, numpy, matplotlib, fastapi, uvicorn, etc.)
- **CLI:** Run scripts create/activate `venv/` and run `ctcc.py` with that Python
- **Server:** `server/run_calc_server.command` (or root `run_calc_server.command`) creates/activates the same root `venv/`, installs from root `requirements.txt`, then runs uvicorn from `server/`. When the API runs a calculation, it invokes `ctcc.py` via `sys.executable` (the same Python as the server), so no second venv is needed.

### Auto-Setup Logic

#### CLI Commands
Each `.command` file at repo root includes:
```bash
# Determine Python binary
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Create venv if missing
if [[ ! -d "venv" ]]; then
  "$PYTHON_BIN" -m venv venv
fi

# Activate and install dependencies
source "venv/bin/activate"
python -m pip install -r requirements.txt

# Run calculation
python ctcc.py [flags]
```

#### API Server
`server/run_calc_server.command` (and root `run_calc_server.command`) sets `VENV_DIR` to the repo root `venv/`, creates/activates it if missing, runs `pip install -r requirements.txt` from repo root, then runs uvicorn from the server directory. The server uses `sys.executable` to run `ctcc.py`, so the same venv is used for both.

## Verification

To verify auto-setup works:

1. **Fresh clone test:**
   ```bash
   git clone <repo>
   cd CTCC
   # No manual setup!
   ./run_json_json.command  # Should work immediately
   ```

2. **API test:**
   ```bash
   cd server
   ./run_calc_server.command  # Should work immediately
   # Open http://localhost:8000 and click Calculate
   ```

3. **Simulated fresh clone:**
   ```bash
   # Backup and remove venv
   mv venv venv.backup

   # Test auto-setup
   ./run_json_json.command

   # Restore
   mv venv.backup venv
   ```

## What's in .gitignore

```
# Virtual environments (NOT committed to git)
.env
.venv
env/
venv/
```

## Troubleshooting

### "Python interpreter not found"
**Solution:** Install Python 3.8+ or set `PYTHON_BIN` environment variable:
```bash
export PYTHON_BIN=/path/to/python3
./run_json_json.command
```

### "Permission denied"
**Solution:** Make command files executable:
```bash
chmod +x *.command
chmod +x server/*.command
```

### "Module not found" despite auto-setup
**Cause:** Partial venv installation or corrupted venv

**Solution:** Delete and let it recreate:
```bash
rm -rf venv
./run_json_json.command  # Auto-creates fresh venv
```

### Auto-setup takes too long
**Cause:** First-time setup downloads and installs dependencies

**Note:** This only happens once. Subsequent runs detect existing venv and skip installation.

## Summary

✅ **No manual venv setup required**
✅ **Works on fresh clone immediately**
✅ **Single venv for CLI and API**
✅ **Dependencies auto-install from one requirements.txt**

Your colleague can clone, run, and calculate without any Python environment setup!
