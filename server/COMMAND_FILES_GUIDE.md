# Server command files

This directory has one command file. The FastAPI process is started from the repo root with `./run_calc_server.command`, not from here.

## `regenerate_json_from_yaml.command`

Converts every `yamls/*.yaml` file into a matching file under `server/json/`, then rebuilds `server/json/final_combined.json` (skips `project_category_template`). Uses the repo-root `venv`.

```bash
# From this directory
./regenerate_json_from_yaml.command
```

Run after editing YAML templates when you want the on-disk JSON copies updated immediately. `GET /api/final_combined` also regenerates `final_combined.json` from YAML when those files change, so this command is optional for a running server.
