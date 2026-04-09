"""
web.py — Interface web do Toolbox via FastAPI.

A classe ToolboxWeb inicializa o app FastAPI, registra dinamicamente
um endpoint POST para cada plugin e delega a personalização do
Swagger ao ToolboxSwagger.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from basetool import BaseTool
from swagger import ToolboxSwagger


# Modelo de entrada genérico compartilhado entre todos os endpoints.
# Aceita qualquer campo no body — a validação fica a cargo de cada plugin.
# O schema real exibido no Swagger é injetado pelo ToolboxSwagger.
class _DynamicInput(BaseModel):
    model_config = {"extra": "allow"}


class ToolboxWeb:
    """
    Inicializa o FastAPI e expõe um endpoint POST para cada plugin registrado.

    Fluxo de uso:
        1. Instanciar: web = ToolboxWeb()
        2. Registrar plugins: web.register_tool(minha_ferramenta)
        3. Ativar Swagger: web.setup_swagger()
        4. Expor o app: app = web.app
    """

    def __init__(self) -> None:
        self.app = FastAPI(
            title="ToolboxTDS",
            description=(
                "Sistema modular de ferramentas (Toolbox) via API REST.\n\n"
                "Cada endpoint abaixo corresponde a um **plugin** independente.\n"
                "Use o Swagger UI para testar as ferramentas interativamente."
            ),
            version="1.0.0",
        )
        # Armazena os schemas OpenAPI de cada plugin para injeção posterior
        self._tool_schemas: dict[str, dict] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """
        Cria o endpoint POST /api/tools/{tool.name} e armazena o schema
        OpenAPI do plugin para ser injetado pelo setup_swagger().

        Usa closure (make_handler) para garantir que cada rota capture
        a referência correta da ferramenta durante a iteração.
        """
        # Guarda o schema do plugin para uso posterior na geração do OpenAPI
        self._tool_schemas[tool.name] = tool.get_swagger_schema()

        # Closure: captura 't' corretamente em cada chamada do loop
        def make_handler(t: BaseTool):
            async def handler(body: _DynamicInput):
                # Converte o modelo Pydantic para dict e repassa ao plugin
                return t.execute(**body.model_dump())
            return handler

        # Registra a rota dinamicamente no FastAPI
        self.app.add_api_route(
            path=f"/api/tools/{tool.name}",
            endpoint=make_handler(tool),
            methods=["POST"],
            tags=[tool.name],
            name=tool.name,
            summary=f"Executar {tool.name}",
        )

    def setup_swagger(self) -> None:
        """
        Substitui o gerador padrão do FastAPI pelo ToolboxSwagger personalizado.
        DEVE ser chamado somente após todos os plugins terem sido registrados.
        """
        swagger = ToolboxSwagger(self.app, self._tool_schemas)
        # Substitui a função de geração do OpenAPI do FastAPI
        self.app.openapi = swagger.generate
