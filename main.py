"""
main.py — Ponto de entrada e orquestrador do ToolboxTDS.

Responsável por:
  1. Instanciar a interface web (ToolboxWeb)
  2. Registrar todos os plugins definidos em config.py
  3. Ativar a geração personalizada do Swagger
  4. Expor o app FastAPI para o uvicorn

Para rodar em desenvolvimento:
    uvicorn main:app --reload

Para rodar diretamente:
    python main.py
"""

import uvicorn

from config import ACTIVE_TOOLS
from web import ToolboxWeb

# 1. Inicializa a interface web (FastAPI)
toolbox = ToolboxWeb()

# 2. Registra cada plugin como um endpoint dinâmico
for ferramenta in ACTIVE_TOOLS:
    toolbox.register_tool(ferramenta)

# 3. Injeta os schemas personalizados no Swagger UI
#    (deve ser chamado APÓS todos os register_tool)
toolbox.setup_swagger()

# 4. Expõe 'app' para o uvicorn encontrar via "main:app"
app = toolbox.app


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
