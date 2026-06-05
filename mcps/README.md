# MCP tool descriptors (optional)

JSON files under `*/tools/` are **cached inbound MCP schemas** used when
`AX_MERGE_INBOUND_MCPS=true` (default). They are not required at runtime if you
only use outbound tools from `profiles/tools/mcp_tools.json`.

To disable merging: set `AX_MERGE_INBOUND_MCPS=false` in `.env`, or point
`AX_MCPS_DIR` at a local directory you maintain outside git.