"""
swagger.py — Geração e personalização do schema OpenAPI (Swagger UI).

A classe ToolboxSwagger substitui o gerador padrão do FastAPI,
mesclando os schemas individuais fornecidos por cada plugin.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


class ToolboxSwagger:
    """
    Responsável por construir o documento OpenAPI final.

    Recebe o app FastAPI e um dicionário {tool_name: schema_dict}
    e, ao ser chamada como app.openapi, retorna o schema completo
    com os metadados detalhados de cada plugin injetados.
    """

    def __init__(self, app: FastAPI, tool_schemas: dict[str, dict]) -> None:
        self.app = app
        # Mapa de nome do plugin → dicionário OpenAPI retornado por get_swagger_schema()
        self.tool_schemas = tool_schemas

    def generate(self) -> dict:
        """
        Gera o schema OpenAPI base via FastAPI e mescla os schemas
        de cada plugin sobre as rotas correspondentes.

        Usa cache interno do FastAPI (app.openapi_schema) para evitar
        regeneração a cada request do Swagger UI.
        """
        # Retorna do cache se o schema já foi gerado anteriormente
        if self.app.openapi_schema:
            return self.app.openapi_schema

        # Gera o schema base a partir das rotas registradas no FastAPI
        schema = get_openapi(
            title=self.app.title,
            version=self.app.version,
            description=self.app.description,
            routes=self.app.routes,
        )

        # Injeta o schema personalizado de cada plugin na rota correspondente
        for tool_name, tool_schema in self.tool_schemas.items():
            path_key = f"/api/tools/{tool_name}"
            if path_key in schema.get("paths", {}):
                # .update() mescla o schema do plugin sobre o gerado automaticamente
                schema["paths"][path_key]["post"].update(tool_schema)

        # Armazena em cache para requisições futuras
        self.app.openapi_schema = schema
        return schema
