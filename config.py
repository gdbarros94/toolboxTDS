"""
config.py — Registro dos plugins ativos no Toolbox.

Este é o único arquivo que precisa ser editado para adicionar
ou remover ferramentas do sistema. Basta instanciar o plugin
e adicioná-lo à lista ACTIVE_TOOLS.
"""

from basetool import BaseTool
from tools.viacep import ViaCepTool

# Lista de ferramentas ativas no Toolbox.
# Adicione novos plugins aqui — o resto do sistema os detecta automaticamente.
ACTIVE_TOOLS: list[BaseTool] = [
    ViaCepTool(),
    # MinhaNovaFerramenta(),  ← adicione novos plugins aqui
]
