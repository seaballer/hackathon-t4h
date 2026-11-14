"""
Servidor MCP Mock para testes e desenvolvimento.
Fornece endpoints simulados para o cliente MCP.
"""

from fastapi import APIRouter
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import asyncio
import logging
import json
import os
import subprocess
import sys
from datetime import datetime
import socket

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAINEL_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painel.html")

app = FastAPI(title="MCP Server Mock", version="1.0.0")

# Histórico do que os agentes fizeram (mostrado no painel)
atividades: List[Dict[str, Any]] = []
_contador_eventos = 1
_processo_agentes: Optional[subprocess.Popen] = None


def registrar_atividade(tipo: str, titulo: str, detalhe: Any = None) -> None:
    """Guarda uma ação no histórico exibido no painel."""
    atividades.append({
        "hora": datetime.now().strftime("%H:%M:%S"),
        "tipo": tipo,
        "titulo": titulo,
        "detalhe": detalhe,
    })
    del atividades[:-200]  # mantém só as 200 mais recentes

def _agora() -> str:
    """Data/hora no mesmo formato do servidor oficial (ex.: 'sab 14/11/2026 16:30')."""
    dias = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    d = datetime.now()
    return f"{dias[d.weekday()]} {d.strftime('%d/%m/%Y %H:%M')}"


def _novo_evento(id_evento: str, de: str, nome: str, assunto: str, corpo: str,
                 origem: str = "cenario") -> Dict[str, Any]:
    """Evento no mesmo formato do servidor oficial (mundo.py)."""
    return {
        "id": id_evento, "de": de, "nome": nome, "assunto": assunto, "corpo": corpo,
        "chegou_em": _agora(), "status": "novo", "responde_a": None,
        "origem": origem, "acoes": [],
    }


# Simulação de dados
eventos_simulados: List[Dict[str, Any]] = [
    _novo_evento(
        "PED-001", "colaborador@t4h.exemplo", "Colaborador Exemplo",
        "Consulta de equipamento",
        "Oi, queria saber qual equipamento está no meu nome (PAT-001).",
    )
]
eventos_entregues: Dict[str, Dict[str, Any]] = {}

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


@app.get("/", response_class=HTMLResponse)
async def root():
    """Painel web do projeto."""
    with open(PAINEL_HTML, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/info")
async def info():
    """Status do servidor (antigo retorno de /)."""
    return {
        "nome": "MCP Server Mock",
        "versao": "1.0.0",
        "status": "online"
    }


# ---------------------------------------------------------------- painel


def _ler_log_agentes(linhas: int = 60) -> List[str]:
    caminho = os.path.join(BASE_DIR, "agentes.log")
    if not os.path.exists(caminho):
        return []
    with open(caminho, "rb") as f:
        bruto = f.read()[-40000:]
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        texto = bruto.decode("cp1252", errors="replace")
    return texto.splitlines()[-linhas:]


class NovoEventoRequest(BaseModel):
    de: str = "colaborador@t4h.exemplo"
    nome: str = "Colaborador Exemplo"
    assunto: str
    corpo: str


@app.get("/api/estado")
async def estado():
    """Tudo que o painel mostra."""
    rodando = _processo_agentes is not None and _processo_agentes.poll() is None
    return {
        "fila": eventos_simulados,
        "inventario": inventario_simulado,
        "atividades": list(reversed(atividades)),
        "log": _ler_log_agentes(),
        "agentes_rodando": rodando,
    }


@app.post("/api/eventos")
async def criar_evento(req: NovoEventoRequest):
    """Coloca um evento novo na fila (botão 'Novo evento' do painel)."""
    global _contador_eventos
    _contador_eventos += 1
    evento = _novo_evento(f"PED-{_contador_eventos:03d}", req.de, req.nome,
                          req.assunto, req.corpo, origem="painel")
    eventos_simulados.append(evento)
    registrar_atividade("evento", f"Evento {evento['id']} criado no painel",
                        f"{req.nome}: {req.assunto}")
    return evento


@app.post("/api/executar_agentes")
async def executar_agentes(request: Request, max_eventos: int = 1):
    """Roda o main.py (time de agentes) contra este servidor."""
    global _processo_agentes
    if _processo_agentes is not None and _processo_agentes.poll() is None:
        raise HTTPException(status_code=409, detail="Os agentes já estão rodando")
    porta = request.url.port
    _processo_agentes = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, "main.py"),
         "--mcp-url", f"http://127.0.0.1:{porta}/mcp",
         "--max-eventos", str(max_eventos)],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    registrar_atividade("agentes", f"Time de agentes iniciado (até {max_eventos} evento(s))")
    return {"iniciado": True, "pid": _processo_agentes.pid}


# ---------------------------------------------------------------- MCP


@app.get("/mcp/proximo_evento")
async def proximo_evento(esperar_segundos: int = 30) -> Dict[str, Any]:
    """Obtém o próximo evento da fila (mesmo formato do servidor oficial).

    Como no servidor oficial, espera até `esperar_segundos` por um evento
    antes de responder "sem evento" (long-poll). Isso evita que os agentes
    fiquem em laço chamando o servidor centenas de vezes por segundo.
    """
    limite = asyncio.get_event_loop().time() + max(0, min(esperar_segundos, 25))
    while not eventos_simulados and asyncio.get_event_loop().time() < limite:
        await asyncio.sleep(0.5)

    if eventos_simulados:
        evento = eventos_simulados.pop(0)
        evento["status"] = "lido"
        eventos_entregues[evento["id"]] = evento
        logger.info(f"Retornando evento: {evento['id']}")
        registrar_atividade("evento", f"Evento {evento['id']} entregue aos agentes",
                            f"{evento['nome']}: {evento['assunto']}")
        return {"status": "ok", "evento": evento, "encerrado": False, "agora": _agora()}

    return {
        "status": "ok",
        "evento": None,
        "mensagem": "Nenhum evento novo agora. Espere e pergunte de novo.",
        "encerrado": False,
        "agora": _agora(),
    }


@app.get("/mcp/ler_evento")
async def ler_evento(evento_id: str) -> Dict[str, Any]:
    """Lê um evento específico."""
    logger.info(f"Lendo evento: {evento_id}")
    if evento_id not in eventos_entregues:
        raise HTTPException(status_code=404, detail=f"Evento {evento_id} não encontrado")
    return {"status": "ok", "evento": eventos_entregues[evento_id]}


@app.post("/mcp/responder_evento")
async def responder_evento(request: ResponderEventoRequest) -> ResponderEventoResponse:
    """Responde a um evento."""
    logger.info(f"Respondendo evento: {request.evento_id}")
    registrar_atividade("resposta", f"Resposta ao evento {request.evento_id}", request.resposta)
    return {
        "sucesso": True,
        "mensagem": f"Resposta registrada para evento {request.evento_id}"
    }


@app.post("/mcp/enviar_mensagem")
async def enviar_mensagem(request: EnviarMensagemRequest) -> EnviarMensagemResponse:
    """Envia uma mensagem."""
    logger.info(f"Enviando mensagem para: {request.destinatario}")
    registrar_atividade("mensagem", f"Mensagem para {request.destinatario}: {request.assunto}",
                        request.corpo)
    return {
        "sucesso": True,
        "mensagem_id": f"msg_{datetime.now().timestamp()}"
    }


@app.post("/mcp/consultar_inventario")
async def consultar_inventario(request: ConsultarInventarioRequest) -> ConsultarInventarioResponse:
    """Consulta o inventário com filtros opcionais."""
    logger.info(f"Consultando inventário com filtros: {request.filtros}")
    registrar_atividade("consulta", "Consulta ao inventário", request.filtros or "sem filtros")

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
        registrar_atividade("atualizacao", f"Inventário {request.patrimonio} atualizado",
                            request.atualizacoes)
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
    registrar_atividade("atualizacao", f"Registro na base {base}", dados)
    return {
        "sucesso": True,
        "id": f"reg_{datetime.now().timestamp()}",
        "mensagem": f"Dados registrados em {base}"
    }


@app.post("/mcp/atualizar")
async def atualizar(base: str, id_registro: str, atualizacoes: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza um registro em uma base."""
    logger.info(f"Atualizando registro {id_registro} em base: {base}")
    registrar_atividade("atualizacao", f"Registro {id_registro} atualizado na base {base}",
                        atualizacoes)
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


def encontrar_porta_disponivel(porta_inicial: int = 8766, max_tentativas: int = 10) -> int:
    """Encontra uma porta disponível começando de porta_inicial."""
    for porta in range(porta_inicial, porta_inicial + max_tentativas):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", porta))
                logger.info(f"Porta {porta} disponível")
                return porta
        except OSError:
            logger.debug(f"Porta {porta} em uso, tentando próxima...")
            continue
    raise RuntimeError(
        f"Nenhuma porta disponível entre {porta_inicial} e {porta_inicial + max_tentativas}")


def iniciar_servidor(host: str = "127.0.0.1", porta: int = 8766):
    """Inicia o servidor MCP."""
    # Encontrar porta disponível
    porta_disponivel = encontrar_porta_disponivel(porta)
    logger.info(f"Iniciando servidor MCP em {host}:{porta_disponivel}")

    # Salvar porta em arquivo para que main.py possa ler
    with open(".mcp_port", "w") as f:
        f.write(str(porta_disponivel))

    uvicorn.run(app, host=host, port=porta_disponivel, log_level="info")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    iniciar_servidor()
