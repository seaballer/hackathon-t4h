"""
Servidor MCP Mock para testes e desenvolvimento.
Fornece endpoints simulados para o cliente MCP.
"""

from fastapi import APIRouter
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server Mock", version="1.0.0")

# Simulação de dados
eventos_simulados = [
    {
        "evento_id": "evt_001",
        "tipo": "consulta_estoque",
        "origem": "email",
        "timestamp": datetime.now().isoformat(),
        "dados": {
            "patrimonio": "PAT-001",
            "colaborador_id": "COL-001"
        }
    }
]

inventario_simulado = {
    "PAT-001": {
        "nome": "Notebook Dell",
        "status": "ativo",
        "colaborador_id": "COL-001",
        "data_aquisicao": "2023-01-15"
    },
    "PAT-002": {
        "nome": "Monitor LG",
        "status": "ativo",
        "colaborador_id": "COL-001",
        "data_aquisicao": "2023-02-20"
    }
}


class ProximoEventoResponse(BaseModel):
    evento_id: str
    tipo: str
    origem: str
    timestamp: str
    dados: Dict[str, Any]


class ResponderEventoRequest(BaseModel):
    evento_id: str
    resposta: str


class ResponderEventoResponse(BaseModel):
    sucesso: bool
    mensagem: str


class EnviarMensagemRequest(BaseModel):
    destinatario: str
    assunto: str
    corpo: str
    evento_id: Optional[str] = None


class EnviarMensagemResponse(BaseModel):
    sucesso: bool
    mensagem_id: str


class ConsultarInventarioRequest(BaseModel):
    filtros: Optional[Dict[str, Any]] = None


class ConsultarInventarioResponse(BaseModel):
    itens: List[Dict[str, Any]]
    total: int


class AtualizarInventarioRequest(BaseModel):
    patrimonio: str
    atualizacoes: Dict[str, Any]


class AtualizarInventarioResponse(BaseModel):
    sucesso: bool
    mensagem: str


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "nome": "MCP Server Mock",
        "versao": "1.0.0",
        "status": "online"
    }


@app.get("/mcp/proximo_evento")
async def proximo_evento(esperar_segundos: int = 30) -> ProximoEventoResponse:
    """Obtém o próximo evento da fila."""
    if eventos_simulados:
        evento = eventos_simulados.pop(0)
        logger.info(f"Retornando evento: {evento['evento_id']}")
        return evento

    # Se não há eventos, retorna um evento simulado
    logger.warning("Nenhum evento na fila, retornando evento simulado")
    return {
        "evento_id": "evt_sim_001",
        "tipo": "consulta_estoque",
        "origem": "sistema",
        "timestamp": datetime.now().isoformat(),
        "dados": {
            "patrimonio": "PAT-001",
            "colaborador_id": "COL-001"
        }
    }


@app.get("/mcp/ler_evento")
async def ler_evento(evento_id: str) -> Dict[str, Any]:
    """Lê um evento específico."""
    logger.info(f"Lendo evento: {evento_id}")
    return {
        "evento_id": evento_id,
        "tipo": "consulta_estoque",
        "origem": "email",
        "timestamp": datetime.now().isoformat(),
        "dados": {
            "patrimonio": "PAT-001",
            "colaborador_id": "COL-001"
        }
    }


@app.post("/mcp/responder_evento")
async def responder_evento(request: ResponderEventoRequest) -> ResponderEventoResponse:
    """Responde a um evento."""
    logger.info(f"Respondendo evento: {request.evento_id}")
    return {
        "sucesso": True,
        "mensagem": f"Resposta registrada para evento {request.evento_id}"
    }


@app.post("/mcp/enviar_mensagem")
async def enviar_mensagem(request: EnviarMensagemRequest) -> EnviarMensagemResponse:
    """Envia uma mensagem."""
    logger.info(f"Enviando mensagem para: {request.destinatario}")
    return {
        "sucesso": True,
        "mensagem_id": f"msg_{datetime.now().timestamp()}"
    }


@app.post("/mcp/consultar_inventario")
async def consultar_inventario(request: ConsultarInventarioRequest) -> ConsultarInventarioResponse:
    """Consulta o inventário com filtros opcionais."""
    logger.info(f"Consultando inventário com filtros: {request.filtros}")

    itens = list(inventario_simulado.values())

    # Aplicar filtros se fornecidos
    if request.filtros:
        for chave, valor in request.filtros.items():
            itens = [item for item in itens if item.get(chave) == valor]

    return {
        "itens": itens,
        "total": len(itens)
    }


@app.post("/mcp/atualizar_inventario")
async def atualizar_inventario(request: AtualizarInventarioRequest) -> AtualizarInventarioResponse:
    """Atualiza um item do inventário."""
    logger.info(f"Atualizando inventário: {request.patrimonio}")

    if request.patrimonio in inventario_simulado:
        inventario_simulado[request.patrimonio].update(request.atualizacoes)
        return {
            "sucesso": True,
            "mensagem": f"Inventário atualizado para {request.patrimonio}"
        }

    raise HTTPException(
        status_code=404, detail=f"Patrimônio {request.patrimonio} não encontrado")


@app.post("/mcp/registrar")
async def registrar(base: str, dados: Dict[str, Any]) -> Dict[str, Any]:
    """Registra dados em uma base."""
    logger.info(f"Registrando dados em base: {base}")
    return {
        "sucesso": True,
        "id": f"reg_{datetime.now().timestamp()}",
        "mensagem": f"Dados registrados em {base}"
    }


@app.post("/mcp/atualizar")
async def atualizar(base: str, id_registro: str, atualizacoes: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza um registro em uma base."""
    logger.info(f"Atualizando registro {id_registro} em base: {base}")
    return {
        "sucesso": True,
        "mensagem": f"Registro {id_registro} atualizado em {base}"
    }


@app.get("/health")
async def health():
    """Verifica a saúde do servidor."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


def iniciar_servidor(host: str = "0.0.0.0", porta: int = 8765):
    """Inicia o servidor MCP."""
    logger.info(f"Iniciando servidor MCP em {host}:{porta}")
    uvicorn.run(app, host=host, port=porta, log_level="info")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    iniciar_servidor()
