"""
ToolboxTDS - Sistema de Plugins via FastAPI
============================================
Arquitetura modular onde cada "ferramenta" é um plugin independente
que descreve seus próprios parâmetros via OpenAPI/Swagger.

Dependências:
    pip install fastapi uvicorn requests

Para rodar:
    uvicorn toolbox:app --reload
"""

import requests
from abc import ABC, abstractmethod
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel


# ===========================================================================
# CLASSE BASE — Todo plugin DEVE herdar desta classe
# ===========================================================================

class BaseTool(ABC):
    """
    Contrato que todo plugin do Toolbox deve cumprir.
    Cada ferramenta precisa saber EXECUTAR e saber se DESCREVER (Swagger).
    """

    # Nome único da ferramenta — usado como slug no endpoint /api/tools/{name}
    name: str = ""

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Lógica real da ferramenta.
        Recebe os parâmetros como kwargs e retorna qualquer valor serializável.
        """
        ...

    @abstractmethod
    def get_swagger_schema(self) -> dict:
        """
        Retorna um dicionário compatível com a especificação OpenAPI 3.x
        descrevendo os parâmetros de entrada e as respostas desta ferramenta.
        Este dicionário é injetado diretamente no schema do FastAPI.
        """
        ...


# ===========================================================================
# FERRAMENTA: ViaCEP — busca endereço a partir de um CEP brasileiro
# ===========================================================================

class ViaCepTool(BaseTool):
    """Plugin que consulta o serviço público ViaCEP."""

    # Slug que define o endpoint: POST /api/tools/viacep
    name = "viacep"

    def execute(self, **kwargs) -> dict:
        """
        Recebe 'cep' via kwargs, consulta a API ViaCEP e retorna o endereço.
        Lança HTTPException em caso de CEP inválido ou erro na consulta.
        """
        cep: str = kwargs.get("cep", "")

        # Sanitização básica: remove traços e espaços
        cep = cep.replace("-", "").replace(" ", "").strip()

        # Validação simples: CEP deve ter 8 dígitos numéricos
        if not cep.isdigit() or len(cep) != 8:
            raise HTTPException(
                status_code=400,
                detail="CEP inválido. Informe 8 dígitos numéricos."
            )

        # Chamada à API externa
        try:
            resposta = requests.get(
                f"https://viacep.com.br/ws/{cep}/json/",
                timeout=5
            )
            resposta.raise_for_status()
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Timeout ao consultar ViaCEP.")
        except requests.exceptions.RequestException as erro:
            raise HTTPException(status_code=502, detail=f"Erro ao consultar ViaCEP: {erro}")

        dados = resposta.json()

        # A API ViaCEP retorna {"erro": true} para CEPs inexistentes
        if dados.get("erro"):
            raise HTTPException(status_code=404, detail="CEP não encontrado.")

        return dados

    def get_swagger_schema(self) -> dict:
        """
        Descreve esta ferramenta no formato OpenAPI 3.x.
        Este dicionário será mesclado diretamente no schema do FastAPI.
        """
        return {
            # --- Descrição do endpoint ---
            "summary": "Busca endereço por CEP",
            "description": (
                "Consulta o serviço público **ViaCEP** e retorna os dados de "
                "endereço correspondentes ao CEP informado. "
                "Aceita CEP com ou sem hífen."
            ),
            "tags": ["Localização"],

            # --- Corpo da requisição (requestBody) ---
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["cep"],
                            "properties": {
                                "cep": {
                                    "type": "string",
                                    "description": "CEP a ser consultado (com ou sem hífen).",
                                    "example": "01310-100"
                                }
                            }
                        }
                    }
                }
            },

            # --- Respostas possíveis ---
            "responses": {
                "200": {
                    "description": "Endereço encontrado com sucesso.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "cep":        {"type": "string", "example": "01310-100"},
                                    "logradouro": {"type": "string", "example": "Avenida Paulista"},
                                    "complemento":{"type": "string", "example": "de 1 a 610 - lado par"},
                                    "bairro":     {"type": "string", "example": "Bela Vista"},
                                    "localidade": {"type": "string", "example": "São Paulo"},
                                    "uf":         {"type": "string", "example": "SP"},
                                    "ibge":       {"type": "string", "example": "3550308"},
                                    "ddd":        {"type": "string", "example": "11"}
                                }
                            }
                        }
                    }
                },
                "400": {
                    "description": "CEP inválido (formato incorreto).",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {"type": "string", "example": "CEP inválido. Informe 8 dígitos numéricos."}
                                }
                            }
                        }
                    }
                },
                "404": {
                    "description": "CEP não encontrado na base do ViaCEP.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {"type": "string", "example": "CEP não encontrado."}
                                }
                            }
                        }
                    }
                },
                "502": {
                    "description": "Erro ao se comunicar com o ViaCEP."
                },
                "504": {
                    "description": "Timeout ao consultar o ViaCEP."
                }
            }
        }


# ===========================================================================
# GERENCIADOR — Inicializa o FastAPI e registra os plugins dinamicamente
# ===========================================================================

class ToolboxManager:
    """
    Coração do sistema.
    Recebe uma lista de plugins (instâncias de BaseTool), cria um endpoint
    dinâmico para cada um e injeta o schema Swagger correspondente.
    """

    def __init__(self, tools: list[BaseTool]):
        # Criação da instância do FastAPI com metadados gerais
        self.app = FastAPI(
            title="ToolboxTDS",
            description=(
                "Sistema modular de ferramentas (Toolbox) via API REST.\n\n"
                "Cada endpoint abaixo corresponde a um **plugin** independente.\n"
                "Use o Swagger UI para testar as ferramentas interativamente."
            ),
            version="1.0.0"
        )

        # Registra cada plugin como um endpoint e guarda seu schema
        self._tool_schemas: dict[str, dict] = {}
        for tool in tools:
            self._register_tool(tool)

        # Substitui a geração padrão do OpenAPI schema pelo nosso customizado
        self.app.openapi = self._custom_openapi

    def _register_tool(self, tool: BaseTool) -> None:
        """
        Cria um endpoint POST /api/tools/{tool.name} para o plugin recebido.
        Usa closure para capturar a referência correta da ferramenta.
        """
        # Guarda o schema do plugin para uso posterior na geração do OpenAPI
        self._tool_schemas[tool.name] = tool.get_swagger_schema()

        # --- Modelo de entrada genérico via Pydantic ---
        # O FastAPI exige um modelo de corpo; usamos dict livre (Any)
        # A validação real fica na responsabilidade de cada plugin.
        class GenericInput(BaseModel):
            class Config:
                extra = "allow"  # Aceita qualquer campo no body

        # Closure: captura 'tool' corretamente em cada iteração do loop
        def make_handler(t: BaseTool):
            async def handler(body: GenericInput):
                # Converte o modelo Pydantic em dict e repassa ao plugin
                return t.execute(**body.model_dump())
            return handler

        # Registra a rota dinamicamente com o nome da ferramenta como tag
        self.app.add_api_route(
            path=f"/api/tools/{tool.name}",
            endpoint=make_handler(tool),
            methods=["POST"],
            tags=[tool.name],
            name=tool.name,
            # summary provisório — será sobrescrito pelo schema customizado abaixo
            summary=f"Executar {tool.name}",
        )

    def _custom_openapi(self) -> dict:
        """
        Gera o schema OpenAPI do FastAPI e então injeta os metadados
        detalhados fornecidos por cada plugin via get_swagger_schema().
        Esta função substitui o gerador padrão do FastAPI.
        """
        # Usa cache para não regenerar a cada request do Swagger UI
        if self.app.openapi_schema:
            return self.app.openapi_schema

        # Gera o schema base do FastAPI
        schema = get_openapi(
            title=self.app.title,
            version=self.app.version,
            description=self.app.description,
            routes=self.app.routes,
        )

        # Injeta os schemas personalizados de cada plugin
        for tool_name, tool_schema in self._tool_schemas.items():
            path_key = f"/api/tools/{tool_name}"

            # Garante que o caminho existe no schema (deve existir após add_api_route)
            if path_key in schema.get("paths", {}):
                # Mescla o schema do plugin sobre o que o FastAPI gerou automaticamente
                schema["paths"][path_key]["post"].update(tool_schema)

        # Armazena em cache
        self.app.openapi_schema = schema
        return schema


# ===========================================================================
# PONTO DE ENTRADA — Instancia os plugins e inicializa o servidor
# ===========================================================================

# Lista de ferramentas ativas no Toolbox
# Para adicionar uma nova ferramenta, basta instanciá-la aqui.
ferramentas_ativas: list[BaseTool] = [
    ViaCepTool(),
    # MinhaNovaFerramenta(),  ← adicione novos plugins aqui
]

# Inicializa o gerenciador e expõe 'app' para o uvicorn
manager = ToolboxManager(tools=ferramentas_ativas)
app = manager.app
