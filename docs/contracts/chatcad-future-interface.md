# ChatCAD future interface boundary

ChatCAD may later read the same exact `board_id` and a future versioned
mechanical section contract after independently verified mechanical data exists.
In this release, CAD intent must return the existing blocked `clarify` route,
must not list `chatcad` as a specialist, and must not claim geometry, DXF, STL,
3D generation or physical-fit capability. No ChatCAD Skill, route, CLI or MCP
tool exists.

```json
{
  "request": {"cad": {"outcome": "mounting bracket"}},
  "required_result": {
    "success": false,
    "route": "clarify",
    "status": "blocked",
    "specialists": []
  }
}
```
