# Virtual Environment Auto-Setup

This document explains how CTCC automatically sets up virtual environments for fresh clones.

## Problem Statement

When a colleague clones the CTCC repository:
- `venv/` and `server/.venv/` are not in git (ignored by `.gitignore`)
- Without these, calculations fail with "ModuleNotFoundError"
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
2. Install dependencies from `requirements.txt` (pyyaml, pandas, numpy)
3. Run calculations using the venv Python

### API Server
When you run:
- `server/run_calc_server.command`

It automatically:
1. Checks if `server/.venv/` exists, create if missing
2. Installs dependencies from `server/requirements.txt` (FastAPI, uvicorn, etc.)
3. **Also ensures `venv/` exists** before running calculations via ctcc.py

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

### Two Separate Virtual Environments

**CLI venv (`venv/`):**
- Used by: `ctcc.py` and all calculation scripts
- Dependencies: pyyaml, pandas, numpy
- Location: `CTCC/venv/`

**Server venv (`server/.venv/`):**
- Used by: FastAPI web server
- Dependencies: fastapi, uvicorn, pydantic
- Location: `CTCC/server/.venv/`

### Why Two Environments?

1. **Separation of concerns:** Web server dependencies vs calculation dependencies
2. **Smaller footprint:** CLI doesn't need FastAPI, server doesn't need full pandas stack
3. **Independent updates:** Can update one without affecting the other

### Auto-Setup Logic

#### CLI Commands
Each `.command` file includes:
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
`server/run_calc_server.command` sets up `server/.venv/`, and `server/app/ctcc_processor.py` includes:
```python
def ensure_cli_venv() -> str:
    """Ensure CLI venv exists and has dependencies."""
    venv_dir = CTCC_ROOT / "venv"

    # Create if missing
    if not venv_dir.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)])

    # Install dependencies
    subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"])

    return str(venv_python)
```

This ensures when the API calls `ctcc.py`, the CLI venv is ready.

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
   # Backup and remove venvs
   mv venv venv.backup
   mv server/.venv server/.venv.backup

   # Test auto-setup
   ./run_json_json.command

   # Restore
   mv venv.backup venv
   mv server/.venv.backup server/.venv
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
rm -rf venv server/.venv
./run_json_json.command  # Auto-creates fresh venv
```

### Auto-setup takes too long
**Cause:** First-time setup downloads and installs dependencies

**Note:** This only happens once. Subsequent runs detect existing venv and skip installation.

## Summary

✅ **No manual venv setup required**
✅ **Works on fresh clone immediately**
✅ **Both CLI and API auto-configure**
✅ **Dependencies auto-install**
✅ **Proper isolation between CLI and server**

Your colleague can clone, run, and calculate without any Python environment setup!
