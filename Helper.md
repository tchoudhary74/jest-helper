# Jest Helper MCP — Setup Guide (DevSpaces)

This repository contains a **Python-based MCP server** used to assist with Jest testing workflows.  
Once running, it integrates with Claude via MCP and operates on a target project (defined by `PROJECT_ROOT`).

Follow the steps below in order. This setup is intentionally strict to avoid environment issues.

-----

## Prerequisites

- DevSpaces access
- Python available in the workspace
- Artifactory access for Python packages

-----

## Step 1: Clone the Repository

Clone the Jest Helper MCP repo into your DevSpaces workspace.

```bash
git clone <repo-url>
cd mock-server
```

In the examples below, the repo is cloned to:

```
/home/user/app/mock-server
```

If your path differs, update it accordingly in the MCP config.

-----

## Step 2: Configure pip for Artifactory

Before installing anything, export the required pip settings.

```bash
export PIP_TRUSTED_HOST=<your-artifactory-host>
export PIP_INDEX_URL=<your-artifactory-pypi-url>
export PIP_DEFAULT_TIMEOUT=100
```

These must be set in the same terminal session.

-----

## Step 3: Install and Verify uv

Install (or upgrade) uv using Python.

```bash
python -m pip install --upgrade uv
```

Verify the installation:

```bash
uv --version
```

If this fails, fix uv before continuing.

-----

## Step 4: Install Dependencies Using uv

From the root of the cloned repo:

```bash
uv sync --native-tls
```

This installs all required dependencies in a reproducible way.

-----

## Step 5: Activate the Python Virtual Environment

This project runs inside a virtual environment created by uv.

```bash
source .venv/bin/activate
```

You should now see the virtual environment active in your shell.

-----

## Step 6: Add Claude MCP Configuration

Create the following file:

```
.cloud/claude_mcp.json
```

Add the configuration below.

```json
{
  "mcpServers": {
    "jest-helper": {
      "command": "/home/user/app/mock-server/.venv/bin/python",
      "args": [
        "/home/user/app/mock-server/src/jest_helper/server.py"
      ],
      "env": {
        "PROJECT_ROOT": "/home/user/app/riskApps/rdm-ui/rdm-ui"
      }
    }
  }
}
```

**Important Notes**

- `/home/user/app/mock-server`  
  → Path where this repo is cloned
- `args`  
  → Must point to the MCP server entry file inside this repo
- `PROJECT_ROOT`  
  → Path to the project you want this MCP to operate on (not this repo)

Update paths if your workspace layout is different.

-----

## Step 7: Start the MCP Server

With the virtual environment still active:

```bash
python src/jest_helper/server.py
```

You should see logs indicating:

- project root detected
- MCP server started
- ready to accept connections

Leave this running.

-----

## Step 8: Restart DevSpaces

After:

- adding `.cloud/claude_mcp.json`
- starting the MCP server

Restart DevSpaces so Claude picks up the MCP configuration.

This step is required.

-----

## Verification

Once restarted:

- Claude should recognize the jest-helper MCP
- MCP tools should be available
- Test discovery / validation / generation should work

If something fails:

- double-check paths in `claude_mcp.json`
- confirm `.venv` is active
- verify pip / Artifactory env vars

-----

## Quick Checklist

- [ ] Repo cloned under `/home/user/app/mock-server`
- [ ] pip env vars exported
- [ ] uv installed and verified
- [ ] `uv sync --native-tls` completed
- [ ] `.venv` activated
- [ ] `.cloud/claude_mcp.json` added
- [ ] MCP server running
- [ ] DevSpaces restarted

-----

## Notes

- Do not commit `.venv`
- Commit `claude_mcp.json` only if intended for team-wide use
- Restart DevSpaces anytime MCP config changes
