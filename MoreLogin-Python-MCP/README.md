### Step 1: Install `uv`

Run the following command to install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Set Up the Environment

Navigate to the project directory:

```bash
cd /ABSOLUTE/PATH/TO/PARENT/FOLDER/MoreLogin-Python-MCP
```

Create and activate a virtual environment:

```bash
uv venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

Install the required dependencies:

```bash
uv add "mcp[cli]" requests
```

### Step 4: Configure the MCP Server

Create or update the configuration file with the following content:

```json
{
    "mcpServers": {
        "MoreLoginAPI": {
            "command": "uv",
            "args": [
                "--directory",
                "/ABSOLUTE/PATH/TO/PARENT/FOLDER/MoreLogin-Python-MCP",
                "run",
                "browser_profile_mcp_server.py"
            ]
        }
    }
}
```