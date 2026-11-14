#!/usr/bin/env python
"""Script para testar as rotas do servidor MCP."""

from src.mcp_server import app

print("Rotas registradas no app:")
for r in app.routes:
    if hasattr(r, 'path'):
        methods = getattr(r, 'methods', 'N/A')
        print(f"  {r.path} - {methods}")
