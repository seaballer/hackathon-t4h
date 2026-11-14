#!/usr/bin/env python
"""Script para testar se todos os módulos estão funcionando."""

import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

print("=" * 60)
print("TESTE DE IMPORTS - COLABORADOR DIGITAL")
print("=" * 60)

try:
    print("\n1. Testando imports básicos...")
    from src.state import AgentState
    print("   ✅ AgentState importado")

    from src.rules import RegrasEquipamentos
    print("   ✅ RegrasEquipamentos importado")

    from src.clock import Clock
    print("   ✅ Clock importado")

    from src.llm import LLMClient
    print("   ✅ LLMClient importado")

    from src.mcp_client import MCPClient
    print("   ✅ MCPClient importado")

    from src.graph import criar_grafo
    print("   ✅ criar_grafo importado")

    print("\n2. Testando inicialização de componentes...")

    # Testar Clock
    clock = Clock()
    print(f"   ✅ Clock inicializado: {clock.data_str()}")

    # Testar RegrasEquipamentos
    regras = RegrasEquipamentos({})
    print("   ✅ RegrasEquipamentos inicializado")

    # Testar validações
    valido, msg = regras.validar_tipo_evento("duvida")
    assert valido, f"Validação falhou: {msg}"
    print("   ✅ Validação de tipo de evento OK")

    # Testar limite de compra
    pode_comprar = regras.pode_comprar_autonomamente(400.0)
    assert pode_comprar, "Limite de compra falhou"
    print("   ✅ Limite de compra OK")

    # Testar nível de autonomia
    nivel = regras.nivel_autonomia("duvida", {})
    assert nivel in ["FAZ", "PROPÕE", "ESCALA",
                     "FAZ_SOZINHO"], f"Nível inválido: {nivel}"
    print(f"   ✅ Nível de autonomia OK (dúvida → {nivel})")

    print("\n3. Testando agentes...")
    from src.agents.coordenador import coordenador
    print("   ✅ Coordenador importado")

    from src.agents.analista import analista
    print("   ✅ Analista importado")

    from src.agents.revisor import revisor
    print("   ✅ Revisor importado")

    from src.agents.executor import executor
    print("   ✅ Executor importado")

    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    print("\nO colaborador digital está funcionando corretamente!")
    print("\nPróximos passos:")
    print("1. Iniciar servidor MCP: TEMA=equipamentos python mundo.py")
    print("2. Executar agentes: python main.py")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
