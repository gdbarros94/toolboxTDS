"""
tools/viacep.py — Plugin de busca de endereço por CEP (ViaCEP).

Herda de BaseTool e implementa a consulta à API pública viacep.com.br.
"""

import requests
from fastapi import HTTPException

from basetool import BaseTool


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

        # Sanitização: remove traços e espaços
        cep = cep.replace("-", "").replace(" ", "").strip()

        # Validação: CEP deve ter exatamente 8 dígitos numéricos
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
        Este dicionário será mesclado na rota correspondente pelo ToolboxSwagger.
        """
        return {
            "summary": "Busca endereço por CEP",
            "description": (
                "Consulta o serviço público **ViaCEP** e retorna os dados de "
                "endereço correspondentes ao CEP informado. "
                "Aceita CEP com ou sem hífen."
            ),
            "tags": ["Localização"],

            # Descreve o corpo da requisição esperado pelo endpoint
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

            # Descreve as respostas possíveis com seus status HTTP
            "responses": {
                "200": {
                    "description": "Endereço encontrado com sucesso.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "cep":         {"type": "string", "example": "01310-100"},
                                    "logradouro":  {"type": "string", "example": "Avenida Paulista"},
                                    "complemento": {"type": "string", "example": "de 1 a 610 - lado par"},
                                    "bairro":      {"type": "string", "example": "Bela Vista"},
                                    "localidade":  {"type": "string", "example": "São Paulo"},
                                    "uf":          {"type": "string", "example": "SP"},
                                    "ibge":        {"type": "string", "example": "3550308"},
                                    "ddd":         {"type": "string", "example": "11"}
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
                "502": {"description": "Erro ao se comunicar com o ViaCEP."},
                "504": {"description": "Timeout ao consultar o ViaCEP."}
            }
        }
