"""
Cliente MCP com retry, idempotência e circuit breaker.
"""

import httpx
import json
import hashlib
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MCPClient:
    """Cliente HTTP para o servidor MCP com resiliência."""

    def __init__(self, base_url: str = "http://localhost:8765/mcp",
                 timeout: int = 15, max_retries: int = 4):
        """
        Args:
            base_url: URL do servidor MCP
            timeout: timeout em segundos
            max_retries: máximo de tentativas
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=timeout)

        # Circuit breaker
        self.falhas_consecutivas = 0
        self.circuit_aberto = False
        self.tempo_circuit_aberto = 0

        # Idempotência
        self.cache_idempotencia: Dict[str, Any] = {}

    def _gerar_chave_idempotencia(self, tool: str, args: Dict) -> str:
        """Gera chave de idempotência baseada em evento_id + tool + args."""
        chave = f"{args.get('evento_id', '')}:{tool}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(chave.encode()).hexdigest()

    def _verificar_circuit_breaker(self) -> bool:
        """Verifica se o circuit breaker está aberto."""
        if self.circuit_aberto:
            agora = time.time()
            if agora - self.tempo_circuit_aberto > 3:  # 3 segundos
                self.circuit_aberto = False
                self.falhas_consecutivas = 0
                logger.info("Circuit breaker fechado")
                return False
            return True
        return False

    def _registrar_falha(self):
        """Registra uma falha e abre o circuit breaker se necessário."""
        self.falhas_consecutivas += 1
        if self.falhas_consecutivas >= 5:
            self.circuit_aberto = True
            self.tempo_circuit_aberto = time.time()
            logger.warning("Circuit breaker aberto após 5 falhas consecutivas")

    def _registrar_sucesso(self):
        """Registra um sucesso e reseta o contador."""
        self.falhas_consecutivas = 0

    def _fazer_requisicao(self, method: str, endpoint: str,
                          data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Faz requisição com retry e backoff exponencial.

        Args:
            method: GET, POST, etc
            endpoint: caminho do endpoint
            data: payload (para POST)

        Returns:
            resposta JSON
        """
        if self._verificar_circuit_breaker():
            raise Exception("Circuit breaker aberto")

        url = f"{self.base_url}{endpoint}"
        backoff_delays = [0.5, 1, 2]

        for tentativa in range(self.max_retries):
            try:
                if method == "GET":
                    response = self.client.get(url)
                elif method == "POST":
                    response = self.client.post(url, json=data)
                else:
                    raise ValueError(f"Método não suportado: {method}")

                # Sucesso
                if response.status_code == 200:
                    self._registrar_sucesso()
                    return response.json()

                # 503 Service Unavailable - retry
                elif response.status_code == 503:
                    if tentativa < self.max_retries - 1:
                        delay = backoff_delays[min(
                            tentativa, len(backoff_delays) - 1)]
                        logger.warning(f"503 recebido, retry em {delay}s")
                        time.sleep(delay)
                        continue
                    else:
                        self._registrar_falha()
                        raise Exception(
                            f"503 após {self.max_retries} tentativas")

                # 504 Gateway Timeout - verificar antes de repetir
                elif response.status_code == 504:
                    logger.warning(
                        f"504 recebido na tentativa {tentativa + 1}")
                    self._registrar_falha()
                    raise Exception(f"504 Gateway Timeout")

                # 409 Conflict - reconsultar e revalidar
                elif response.status_code == 409:
                    logger.warning(f"409 Conflict recebido")
                    self._registrar_falha()
                    raise Exception(f"409 Conflict - revalidar regra")

                # 410 Gone - parar
                elif response.status_code == 410:
                    logger.error(f"410 Gone - cenário encerrado")
                    raise Exception(f"410 Gone - cenário encerrado")

                else:
                    logger.error(
                        f"Erro HTTP {response.status_code}: {response.text}")
                    self._registrar_falha()
                    raise Exception(f"HTTP {response.status_code}")

            except httpx.TimeoutException:
                logger.warning(f"Timeout na tentativa {tentativa + 1}")
                if tentativa < self.max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    self._registrar_falha()
                    raise

            except Exception as e:
                logger.error(f"Erro na tentativa {tentativa + 1}: {e}")
                if tentativa < self.max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    self._registrar_falha()
                    raise

        raise Exception(f"Falha após {self.max_retries} tentativas")

    def proximo_evento(self, esperar_segundos: int = 30) -> Dict[str, Any]:
        """Obtém o próximo evento da fila."""
        return self._fazer_requisicao("GET",
                                      f"/proximo_evento?esperar_segundos={esperar_segundos}")

    def ler_evento(self, evento_id: str) -> Dict[str, Any]:
        """Lê um evento específico."""
        return self._fazer_requisicao("GET", f"/ler_evento?evento_id={evento_id}")

    def responder_evento(self, evento_id: str, resposta: str) -> Dict[str, Any]:
        """Responde a um evento."""
        chave = self._gerar_chave_idempotencia("responder_evento",
                                               {"evento_id": evento_id})
        if chave in self.cache_idempotencia:
            logger.info(f"Resposta já enviada para {evento_id}")
            return self.cache_idempotencia[chave]

        resultado = self._fazer_requisicao("POST", "/responder_evento",
                                           {"evento_id": evento_id, "resposta": resposta})

        self.cache_idempotencia[chave] = resultado
        return resultado

    def enviar_mensagem(self, destinatario: str, assunto: str,
                        corpo: str, evento_id: Optional[str] = None) -> Dict[str, Any]:
        """Envia uma mensagem."""
        chave = self._gerar_chave_idempotencia("enviar_mensagem",
                                               {"destinatario": destinatario, "assunto": assunto, "evento_id": evento_id})
        if chave in self.cache_idempotencia:
            logger.info(f"Mensagem já enviada para {destinatario}")
            return self.cache_idempotencia[chave]

        resultado = self._fazer_requisicao("POST", "/enviar_mensagem",
                                           {"destinatario": destinatario, "assunto": assunto,
                                            "corpo": corpo, "evento_id": evento_id})

        self.cache_idempotencia[chave] = resultado
        return resultado

    def consultar_inventario(self, filtros: Optional[Dict] = None) -> Dict[str, Any]:
        """Consulta o inventário com filtros opcionais."""
        return self._fazer_requisicao("POST", "/consultar_inventario",
                                      filtros or {})

    def atualizar_inventario(self, patrimonio: str,
                             atualizacoes: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza um item do inventário."""
        chave = self._gerar_chave_idempotencia("atualizar_inventario",
                                               {"patrimonio": patrimonio})
        if chave in self.cache_idempotencia:
            logger.info(f"Inventário já atualizado para {patrimonio}")
            return self.cache_idempotencia[chave]

        resultado = self._fazer_requisicao("POST", "/atualizar_inventario",
                                           {"patrimonio": patrimonio, "atualizacoes": atualizacoes})

        self.cache_idempotencia[chave] = resultado
        return resultado

    def registrar(self, base: str, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Registra dados em uma base."""
        chave = self._gerar_chave_idempotencia("registrar",
                                               {"base": base, "evento_id": dados.get("evento_id")})
        if chave in self.cache_idempotencia:
            logger.info(f"Registro já feito em {base}")
            return self.cache_idempotencia[chave]

        resultado = self._fazer_requisicao("POST", "/registrar",
                                           {"base": base, "dados": dados})

        self.cache_idempotencia[chave] = resultado
        return resultado

    def atualizar(self, base: str, id_registro: str,
                  atualizacoes: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza um registro em uma base."""
        chave = self._gerar_chave_idempotencia("atualizar",
                                               {"base": base, "id": id_registro})
        if chave in self.cache_idempotencia:
            logger.info(f"Registro já atualizado em {base}")
            return self.cache_idempotencia[chave]

        resultado = self._fazer_requisicao("POST", "/atualizar",
                                           {"base": base, "id": id_registro, "atualizacoes": atualizacoes})

        self.cache_idempotencia[chave] = resultado
        return resultado
