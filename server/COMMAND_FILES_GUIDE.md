# CTCC Server Command Files Guide

This directory contains three command files for running different aspects of the CTCC server infrastructure.

---

## 📁 Command Files

### 1. `run_fastapi.command` - FastAPI Server
**Purpose**: Launches the main FastAPI application server with CTCC calculation endpoint.

**What it does:**
- Creates/activates virtual environment (`.venv`)
- Installs/updates dependencies from `requirements.txt`
- Starts Uvicorn server with hot reload
- Reports public, LAN, and local URLs
- Logs all requests to `logs/fastapi_YYYYMMDD_HHMMSS.log`

**Usage:**
```bash
# Double-click in Finder (macOS)
# OR run from terminal:
./run_fastapi.command
```

**Default Settings:**
- Host: `0.0.0.0` (accessible from network)
- Port: `8000`
- Auto-reload: Enabled

**Environment Variables:**
```bash
PORT=8001 ./run_fastapi.command     # Use custom port
HOST=127.0.0.1 ./run_fastapi.command # Localhost only
```

**Dependencies** (from `requirements.txt`):
- fastapi >= 0.110.0
- uvicorn[standard] >= 0.29.0
- pyyaml >= 6.0.0
- pandas >= 2.3.3
- numpy >= 2.3.4

**API Endpoints:**
- `GET /` - Serves web UI (`index.html`)
- `GET /api/final_combined` - Returns combined JSON
- `POST /api/process` - Simple/Bulk demo mode
- `POST /api/ctcc/calculate` - **NEW: CTCC calculations** ⭐

**Access URLs:**
- Local: `http://127.0.0.1:8000`
- LAN: `http://<your-local-ip>:8000`
- Public: `http://<your-public-ip>:8000` (if accessible)

---

### 2. `web_ui_server.command` - Static Web Server
**Purpose**: Serves the HTML/CSS/JS static files using Python's built-in HTTP server.

**What it does:**
- Serves files from `static/` directory
- Reports public, LAN, and local URLs
- Logs requests to `logs/static_server_YYYYMMDD_HHMMSS.log`
- No build step required (pure static)

**Usage:**
```bash
./web_ui_server.command
```

**Default Settings:**
- Host: `0.0.0.0`
- Port: `5500`

**Environment Variables:**
```bash
STATIC_PORT=8080 ./web_ui_server.command  # Use custom port
```

**When to Use:**
- Testing static HTML changes without FastAPI
- Lightweight development server
- Serving static assets separately

**Note**: This server only serves static files. For CTCC calculations, you need `run_fastapi.command`.

---

### 3. `convert_yamls.command` - YAML to JSON Converter
**Purpose**: Converts YAML configuration files to JSON format for API use.

**What it does:**
- Prompts for YAML source directory (with GUI file picker on macOS)
- Converts all `.yaml` and `.yml` files to JSON
- Saves individual JSON files to `json/` directory
- Creates `json/final_combined.json` with all files combined

**Usage:**
```bash
./convert_yamls.command
```

**Interactive Options:**
1. Use `../yamls/` (CTCC project directory)
2. Use `yamls/` (local copy in server)
3. Browse for directory (macOS file picker)

**Output:**
- Individual files: `json/01_project_technical_details.json`, etc.
- Combined file: `json/final_combined.json` ⭐

**When to Use:**
- After updating YAML files in `../yamls/`
- Before testing JSON input mode
- To refresh the combined JSON for API endpoints

**Example Workflow:**
```bash
# 1. Edit YAML files
vim ../yamls/03_financing.yaml

# 2. Convert to JSON
./convert_yamls.command
# Select option 1 (CTCC/yamls/)

# 3. Start server
./run_fastapi.command

# 4. Test in browser
open http://127.0.0.1:8000
```

---

## 🚀 Quick Start Guide

### For Development:
```bash
# Terminal 1: Start FastAPI server
cd server
./run_fastapi.command

# Terminal 2: Watch for changes (optional)
# The server auto-reloads on file changes
```

### For Testing CTCC:
```bash
# 1. Ensure YAMLs are converted to JSON
cd server
./convert_yamls.command

# 2. Start FastAPI server
./run_fastapi.command

# 3. Open web UI
open http://127.0.0.1:8000

# 4. Select "CTCC" mode in the web interface
# 5. Configure input/output modes
# 6. Click "Send JSON"
```

### For Production:
```bash
# Use environment variables for configuration
HOST=0.0.0.0 PORT=8000 ./run_fastapi.command

# Or edit the command file directly
```

---

## 📂 Directory Structure

```
server/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── processor.py            # Demo mode processor
│   └── ctcc_processor.py       # CTCC calculation orchestrator ⭐
├── static/
│   └── index.html              # Web UI with CTCC mode ⭐
├── json/
│   ├── 01_project_technical_details.json
│   ├── 02_project_physical_details.json
│   ├── ...
│   └── final_combined.json     # Combined JSON for API ⭐
├── logs/
│   ├── fastapi_*.log
│   └── static_server_*.log
├── .venv/                      # Virtual environment
├── requirements.txt
├── run_fastapi.command         # ⭐ Main server
├── web_ui_server.command       # Static file server
├── convert_yamls.command       # YAML → JSON converter
└── COMMAND_FILES_GUIDE.md      # This file
```

---

## 🔧 Troubleshooting

### Server Won't Start
**Error**: `Port 8000 already in use`
**Solution**:
```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
PORT=8001 ./run_fastapi.command
```

### Virtual Environment Issues
**Error**: `.venv` creation fails
**Solution**:
```bash
# Delete old venv
rm -rf .venv

# Recreate
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'pyyaml'`
**Solution**:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### YAML Conversion Fails
**Error**: No YAML files found
**Solution**:
```bash
# Check YAML directory exists
ls ../yamls/*.yaml

# Or copy YAMLs locally
cp -r ../yamls ./yamls
./convert_yamls.command
# Select option 2
```

### Can't Access from Network
**Error**: Server not reachable from other devices
**Solution**:
```bash
# Check firewall settings
# Ensure HOST=0.0.0.0 (not 127.0.0.1)
HOST=0.0.0.0 ./run_fastapi.command
```

---

## 🆕 What's New in CTCC Implementation

### Updated Features:

1. **FastAPI Endpoint**: `/api/ctcc/calculate`
   - Accepts JSON input with full configuration
   - Supports YAML mode (server-side files)
   - Returns JSON results or CSV file list
   - Configurable input/output modes

2. **Web UI Enhancements**:
   - New "CTCC" mode alongside Simple/Bulk
   - Input mode selector (JSON/YAML)
   - Output mode selector (JSON/CSV)
   - Scenario ID field (optional)
   - Automatic JSON fetching

3. **JSON Support**:
   - `final_combined.json` contains all 22 YAML files
   - Individual JSON files for each configuration
   - Compatible with API and calculation scripts

4. **Backward Compatibility**:
   - Demo modes (Simple/Bulk) still work
   - Original endpoints unchanged
   - YAML workflow preserved

---

## 📚 Additional Resources

- **Implementation Guide**: `../IMPLEMENTATION_COMPLETE.md`
- **API Documentation**: `../FASTAPI_JSON_RESPONSE.md`
- **System Overview**: `../claude.md`
- **Test Script**: `../test_fastapi_endpoint.py`

---

## 💡 Tips

1. **Auto-reload**: FastAPI server automatically reloads on code changes
2. **Logs**: Check `logs/` directory for detailed request logs
3. **Combined JSON**: Always regenerate after YAML changes
4. **Virtual Env**: Each command manages its own `.venv`
5. **Port Conflicts**: Change port if 8000 is in use
6. **Network Access**: Use `0.0.0.0` to allow LAN access
7. **Testing**: Use `../test_fastapi_endpoint.py` for API tests

---

## 🎯 Next Steps

1. **Start the server**: `./run_fastapi.command`
2. **Open web UI**: `http://127.0.0.1:8000`
3. **Test CTCC mode**: Select CTCC, configure, submit
4. **Check logs**: Review `logs/fastapi_*.log`
5. **Run tests**: `cd .. && python test_fastapi_endpoint.py`

---

**Last Updated**: 2025-11-10
**CTCC Version**: JSON Input/Output Implementation Complete
