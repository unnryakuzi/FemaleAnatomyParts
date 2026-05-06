Blender MCP setup for this workspace

Recommended server
- `blender-mcp` via `uvx`

Why this setup
- Matches the existing allowed tool names in `.claude/settings.local.json` such as `get_scene_info`, `get_object_info`, and `execute_blender_code`.
- Keeps installation light because Codex can launch the server through `uvx` without a separate permanent Python package install.

Workspace MCP config
- `.mcp.json` defines:
  - server name: `blender`
  - command: `uvx blender-mcp`

Blender-side requirement
1. Open `3DAnatomyman_Japanese.blend` in Blender.
2. Install and enable the BlenderMCP add-on (`addon.py` from the BlenderMCP project).
3. In the Blender sidebar, open the `BlenderMCP` tab.
4. Leave the port at `9876` unless you have a conflict.
5. Click `Start MCP Server`.

Codex-side requirement
- Register the same server globally for Codex:
  - `codex mcp add blender -- uvx blender-mcp`

Verification
- `codex mcp list`
- Then restart Codex if the running session does not pick up the new server automatically.
