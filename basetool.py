"""
basetool.py — Contrato base para todos os plugins do Toolbox.
Todo plugin DEVE herdar desta classe e implementar os dois métodos abstratos.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Classe abstrata que define o contrato de todo plugin do Toolbox.

    Cada ferramenta precisa saber:
      1. EXECUTAR  — método execute()
      2. SE DESCREVER — método get_swagger_schema()
    """

    # Nome único da ferramenta — vira slug no endpoint: POST /api/tools/{name}
    name: str = ""

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Lógica real da ferramenta.
        Recebe os campos do body da requisição como keyword arguments
        e retorna qualquer valor JSON-serializável.
        """
        ...

    @abstractmethod
    def get_swagger_schema(self) -> dict:
        """
        Retorna um dicionário compatível com a especificação OpenAPI 3.x
        descrevendo os parâmetros de entrada e as respostas desta ferramenta.
        Este dicionário é injetado diretamente no schema do FastAPI pelo ToolboxSwagger.
        """
        ...
