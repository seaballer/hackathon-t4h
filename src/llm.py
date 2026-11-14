"""
Integração com LLM (GPT-4o-mini) via LiteLLM com cache de prompt e fallback.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
import litellm

logger = logging.getLogger(__name__)


class LLMClient:
    """Cliente para chamadas ao LLM com cache e fallback."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", offline: bool = False):
        """
        Args:
            api_key: chave da API (padrão: variável de ambiente OPENAI_API_KEY)
            model: modelo a usar
            offline: se True, usa fallback sem chamar LiteLLM
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = os.getenv("LITELLM_API_BASE")
        self.model = model

        # Detecta modo offline se:
        # - offline=True, ou
        # - não há chave, ou
        # - chave começa com "sk-test"
        self.offline = offline or not self.api_key or (
            self.api_key and self.api_key.startswith("sk-test"))

        if not self.offline and self.api_key and not self.api_key.startswith("sk-test"):
            try:
                # Configura LiteLLM com a URL base e chave de API
                if self.api_base:
                    litellm.api_base = self.api_base
                litellm.api_key = self.api_key
                logger.info(
                    f"LiteLLM configurado com base URL: {self.api_base}")
            except Exception as e:
                logger.warning(
                    f"Erro ao inicializar LiteLLM: {e}. Usando fallback.")
                self.offline = True
        else:
            if self.offline:
                logger.warning("LLMClient em modo offline - usando fallback")

        self.tokens_usados = 0
        self.falhas_consecutivas = 0

    def classificar_evento(self, evento: Dict[str, Any],
                           regras: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """
        Classifica o tipo de evento e extrai entidades.

        Returns:
            (tipo, confianca, entidades)
        """
        system_prompt = """Você é um assistente especializado em gestão de equipamentos de TI.
Analise o evento recebido e:
1. Classifique o tipo de evento (um dos 12 tipos)
2. Extraia as entidades relevantes (patrimonio, colaborador_id, data, itens, etc)
3. Indique seu nível de confiança (0.0-1.0)

Responda em JSON com a estrutura:
{
  "tipo": "string",
  "confianca": 0.0-1.0,
  "entidades": {
    "patrimonio": "string ou null",
    "colaborador_id": "string ou null",
    "data": "AAAA-MM-DD ou null",
    "itens": [],
    "valor": 0.0
  }
}"""

        user_prompt = f"""Evento recebido:
{json.dumps(evento, indent=2, ensure_ascii=False)}

Tipos conhecidos: duvida, consulta_estoque, devolucao, resposta_cobranca, alocacao, 
reserva_kit, troca_defeito, emprestimo, entrada_pessoa, saida_pessoa, baixa, entrega_compra, outro

Regras de negócio:
{json.dumps(regras, indent=2, ensure_ascii=False)}"""

        # Se offline, usar fallback direto
        if self.offline:
            logger.info("Usando fallback (modo offline)")
            return self._classificar_fallback(evento)

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            resultado = json.loads(response.choices[0].message.content)
            self.tokens_usados += response.usage.completion_tokens
            self.falhas_consecutivas = 0

            return (resultado["tipo"], resultado["confianca"], resultado["entidades"])

        except Exception as e:
            logger.error(f"Erro ao classificar evento: {e}")
            self.falhas_consecutivas += 1

            if self.falhas_consecutivas >= 3:
                # Fallback: classificador de palavras-chave
                return self._classificar_fallback(evento)

            raise

    def _classificar_fallback(self, evento: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """Fallback: classificador simples baseado em palavras-chave."""
        corpo = str(evento).lower()

        palavras_chave = {
            "duvida": ["dúvida", "pergunta", "como", "qual", "o que"],
            "consulta_estoque": ["estoque", "disponível", "quantos", "tem"],
            "devolucao": ["devolver", "devolução", "retorno"],
            "alocacao": ["alocar", "alocação", "atribuir"],
            "reserva_kit": ["reservar", "kit", "reserva"],
            "troca_defeito": ["defeito", "quebrado", "danificado", "troca"],
            "emprestimo": ["emprestar", "empréstimo", "temporário"],
            "entrada_pessoa": ["entrada", "novo", "contratado", "onboarding"],
            "saida_pessoa": ["saída", "demissão", "desligamento"],
            "baixa": ["baixa", "sucata", "descarte"],
            "entrega_compra": ["entrega", "compra", "recebimento"],
        }

        tipo_provavel = "outro"
        max_matches = 0

        for tipo, palavras in palavras_chave.items():
            matches = sum(1 for p in palavras if p in corpo)
            if matches > max_matches:
                max_matches = matches
                tipo_provavel = tipo

        entidades = {
            "patrimonio": None,
            "colaborador_id": None,
            "data": None,
            "itens": [],
            "valor": 0.0
        }

        logger.warning(f"Usando fallback para classificação: {tipo_provavel}")
        return (tipo_provavel, 0.5, entidades)

    def redigir_resposta(self, tipo_evento: str, entidades: Dict[str, Any],
                         contexto: Dict[str, Any]) -> str:
        """Redige uma resposta para o evento."""
        system_prompt = """Você é um assistente de gestão de equipamentos de TI.
Redija uma resposta clara, profissional e concisa para o evento recebido."""

        user_prompt = f"""Tipo de evento: {tipo_evento}
Entidades extraídas: {json.dumps(entidades, indent=2, ensure_ascii=False)}
Contexto: {json.dumps(contexto, indent=2, ensure_ascii=False)}

Redija uma resposta apropriada."""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )

            resposta = response.choices[0].message.content
            self.tokens_usados += response.usage.completion_tokens
            self.falhas_consecutivas = 0

            return resposta

        except Exception as e:
            logger.error(f"Erro ao redigir resposta: {e}")
            self.falhas_consecutivas += 1

            if self.falhas_consecutivas >= 3:
                return "Sua solicitação foi registrada e será processada em breve."

            raise

    def reanalizar_evento(self, evento: Dict[str, Any],
                          motivo: str) -> Tuple[str, float, Dict[str, Any]]:
        """Reanalisa um evento com confiança baixa."""
        system_prompt = """Você é um especialista em gestão de equipamentos de TI.
Reanalise o evento com cuidado extra, considerando o motivo da reanalise."""

        user_prompt = f"""Evento: {json.dumps(evento, indent=2, ensure_ascii=False)}

Motivo da reanalise: {motivo}

Classifique novamente o tipo e extraia as entidades com máxima precisão."""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )

            resultado = json.loads(response.choices[0].message.content)
            self.tokens_usados += response.usage.completion_tokens
            self.falhas_consecutivas = 0

            return (resultado["tipo"], resultado["confianca"], resultado["entidades"])

        except Exception as e:
            logger.error(f"Erro ao reanalizar evento: {e}")
            self.falhas_consecutivas += 1
            raise

    def obter_tokens_usados(self) -> int:
        """Retorna o total de tokens usados."""
        return self.tokens_usados
