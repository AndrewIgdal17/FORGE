# CTCC Setup Guide for Windows

This guide helps Windows users set up and run CTCC.

## Prerequisites

### Install Python 3.8+

1. **Download Python:**
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Download Python 3.8 or higher (3.11+ recommended)

2. **Install Python:**
   - Run the installer
   - ⚠️ **IMPORTANT:** Check the box "Add Python to PATH"
   - Click "Install Now"

3. **Verify Installation:**
   ```cmd
   python --version
   ```
   Should show: `Python 3.x.x`

### If Python is Already Installed (Without PATH)

If you installed Python but forgot to add it to PATH:

**Option 1: Reinstall Python**
- Uninstall Python from Control Panel
- Reinstall and check "Add Python to PATH"

**Option 2: Add to PATH Manually**
1. Find Python installation (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx`)
2. Right-click "This PC" → Properties → Advanced system settings
3. Click "Environment Variables"
4. Under "System variables", select "Path" → Edit
5. Add these two paths:
   - `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx`
   - `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\Scripts`
6. Click OK and restart Command Prompt

**Option 3: Use Python Launcher**
- Windows Python installer includes `py` launcher
- The batch files automatically detect and use `py -3` if `python` isn't found

## Running CTCC on Windows

### CLI Calculations

Open Command Prompt and navigate to CTCC directory:

```cmd
cd path\to\CTCC

REM Run YAML → CSV mode
run_yaml_csv.bat

REM Run JSON → CSV mode
run_json_csv.bat

REM Run JSON → JSON mode
run_json_json.bat
```

### Web Interface (API Server)

```cmd
cd path\to\CTCC\server
run_calc_server.bat
```

Then open your browser to: `http://localhost:8000`

## First Run

On first run, the batch files will:
1. ✅ Detect Python installation
2. ✅ Create virtual environment (`venv\` or `.venv\`)
3. ✅ Install dependencies (pyyaml, pandas, numpy, fastapi, etc.)
4. ✅ Run the calculation or server

This takes 1-2 minutes on first run. Subsequent runs are instant.

## Troubleshooting

### "Python was not found"

**Cause:** Python is not in PATH or not installed

**Solutions:**

1. **Check if Python is installed:**
   ```cmd
   where python
   where python3
   where py
   ```

2. **Try Python Launcher:**
   ```cmd
   py -3 --version
   ```
   If this works, the batch files will automatically use it.

3. **Add Python to PATH:**
   - See "If Python is Already Installed (Without PATH)" above

4. **Reinstall Python:**
   - Download from python.org
   - Check "Add Python to PATH" during installation

### "pip is not recognized"

**Cause:** Python Scripts folder not in PATH

**Solution:**
```cmd
python -m pip install --upgrade pip
```
Use `python -m pip` instead of `pip` directly.

### "'tee' is not recognized"

**Fixed:** The batch files no longer use `tee` (Unix-only command)

### Virtual Environment Creation Fails

**Error:** "Failed to create virtual environment"

**Solutions:**

1. **Check disk space:**
   Ensure at least 500MB free space

2. **Run as Administrator:**
   Right-click Command Prompt → "Run as administrator"

3. **Check Python installation:**
   ```cmd
   python -m venv test_venv
   ```
   If this fails, reinstall Python

4. **Antivirus blocking:**
   Temporarily disable antivirus and try again

### Module Not Found After Setup

**Error:** "ModuleNotFoundError: No module named 'pandas'"

**Cause:** Virtual environment activated but dependencies not installed

**Solution:**
```cmd
cd CTCC
venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

### Server Won't Start (Port Already in Use)

**Error:** "Address already in use"

**Solution:**
```cmd
REM Find process using port 8000
netstat -ano | findstr :8000

REM Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>

REM Or use different port
set PORT=8001
run_calc_server.bat
```

### Long Path Issues

**Error:** "The system cannot find the path specified"

**Cause:** Windows path length limit (260 characters)

**Solution:**
Move CTCC to shorter path:
```cmd
REM Bad (too long)
C:\Users\YourName\Documents\Projects\Research\UT-TransmissionCalc\CTCC

REM Good (short)
C:\CTCC
```

## Performance Tips

### Faster Startup

After first run, to skip dependency reinstall:
```cmd
REM Comment out the pip install lines in batch file
REM Or use existing venv without update
venv\Scripts\activate.bat
python ctcc.py -j -o
```

### Running in Background

To run server in background:
```cmd
start /B run_calc_server.bat
```

## File Locations

### Virtual Environments
- CLI: `CTCC\venv\` (auto-created)
- Server: `CTCC\server\.venv\` (auto-created)

### Outputs
- CSV files: `CTCC\outputs\*.csv`
- JSON results: `CTCC\outputs\ctcc_results_*.json`

### Logs
- Server logs: `CTCC\server\logs\*.log`

## Python Launcher (`py`) vs `python`

Windows Python installer includes a launcher called `py`:

| Command | Description |
|---------|-------------|
| `py` | Launch default Python |
| `py -3` | Launch Python 3.x |
| `py -3.11` | Launch specific version |
| `python` | Only works if in PATH |

The batch files try all three: `python`, `python3`, and `py -3`.

## Common Windows Python Locations

```
C:\Python3xx\
C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\
C:\Program Files\Python3xx\
```

## Differences from Mac/Linux

| Feature | Mac/Linux | Windows |
|---------|-----------|---------|
| Command files | `.command` | `.bat` |
| Path separator | `/` | `\` |
| Venv activate | `source venv/bin/activate` | `venv\Scripts\activate.bat` |
| Python in PATH | Usually automatic | Must check during install |
| Python command | `python3` | `python` or `py` |

## Getting Help

If you're still stuck:

1. **Check Python installation:**
   ```cmd
   python --version
   python -m pip --version
   ```

2. **Check file locations:**
   ```cmd
   dir venv
   dir server\.venv
   dir requirements.txt
   ```

3. **Run Python directly:**
   ```cmd
   python -m venv test_venv
   test_venv\Scripts\activate.bat
   python -m pip install pandas
   ```

4. **Contact the developer:**
   - Include error messages
   - Include Python version (`python --version`)
   - Include Windows version

## Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] Python added to PATH (check "Add Python to PATH" during install)
- [ ] Cloned CTCC repository
- [ ] Opened Command Prompt
- [ ] Navigated to CTCC directory (`cd path\to\CTCC`)
- [ ] Ran batch file (`run_json_json.bat`)
- [ ] First run completed (venv created, dependencies installed)
- [ ] Subsequent runs work instantly

Once the checklist is complete, CTCC is ready to use on Windows!
