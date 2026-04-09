# ToolboxTDS — Modular Plugin API with FastAPI

A modular "toolbox" system where each **tool is a self-describing plugin** served as a REST endpoint. The Swagger UI is automatically populated with the documentation each plugin provides.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Project Structure](#project-structure)
3. [Getting Started](#getting-started)
4. [The Swagger Challenge](#the-swagger-challenge)
5. [How to Add a New Tool (Step-by-Step)](#how-to-add-a-new-tool-step-by-step)
6. [OpenAPI Schema Reference](#openapi-schema-reference)

---

## System Overview

The architecture follows a **plugin pattern** built on top of FastAPI:

```
┌─────────────────────────────────────────────────────────┐
│                      toolbox.py                         │
│                                                         │
│  ┌──────────────┐     registers     ┌────────────────┐  │
│  │ ToolboxManager│ ──────────────►  │  FastAPI app   │  │
│  └──────┬───────┘                  └────────────────┘  │
│         │ iterates                                      │
│         ▼                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │              List[BaseTool instances]            │    │
│  │  ┌───────────┐  ┌───────────┐  ┌─────────────┐  │    │
│  │  │ViaCepTool │  │  Tool B   │  │   Tool C    │  │    │
│  │  └───────────┘  └───────────┘  └─────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**Key components:**

| Component | Role |
|---|---|
| `BaseTool` | Abstract class. Defines the contract every plugin must fulfill. |
| `execute(**kwargs)` | Contains the tool's real logic. Receives the request body as keyword arguments. |
| `get_swagger_schema()` | Returns an OpenAPI-compatible dict that **describes** the tool to the Swagger UI. |
| `ToolboxManager` | Reads the list of active tools, creates a `POST /api/tools/{name}` route for each one, and merges each tool's schema into the final OpenAPI document. |

---

## Project Structure

```
toolboxTDS/
├── toolbox.py   ← single-file application (all plugins live here for now)
└── README.md
```

---

## Getting Started

### 1. Install dependencies

```bash
pip install fastapi uvicorn requests
```

### 2. Run the server

```bash
uvicorn toolbox:app --reload
```

### 3. Open the interactive docs

Navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser.

You will see the Swagger UI with every registered tool ready to be tested.

---

## The Swagger Challenge

### How FastAPI builds its documentation

FastAPI uses the **OpenAPI 3.x specification** to generate the interactive documentation you see at `/docs`. Every route you declare with `@app.get(...)`, `@app.post(...)`, etc., is automatically introspected and added to a large JSON document served at `/openapi.json`.

You can inspect this document directly at [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json).

### Why do plugins need to provide their own schema?

In a dynamic plugin system, routes are created at runtime with `app.add_api_route(...)`. FastAPI can infer basic type information from Pydantic models, but it **cannot know** the business-level semantics of each tool (e.g., "this field is a Brazilian postal code", "the response will contain a street name").

That is why `BaseTool` requires every plugin to implement `get_swagger_schema() -> dict`. This method returns a fragment of the OpenAPI specification that **replaces** the generic, auto-generated documentation for that plugin's endpoint.

### What the ToolboxManager does with it

```python
# Inside ToolboxManager._custom_openapi()
schema["paths"]["/api/tools/viacep"]["post"].update(tool_schema)
```

The manager merges (`update`) the plugin's schema dict on top of whatever FastAPI generated automatically. This is why your schema must follow the **exact OpenAPI 3.x structure** — any unknown key will be silently ignored by the Swagger UI.

> **Your mission as a plugin author:** read the OpenAPI specification and write a valid `get_swagger_schema()` method. The next section walks you through it.

---

## How to Add a New Tool (Step-by-Step)

Let's build a fake example tool: **`EchoTool`** — it simply returns whatever text the user sends.

### Step 1 — Inherit from `BaseTool`

```python
from toolbox import BaseTool  # if splitting into multiple files
# or just add the class directly in toolbox.py

class EchoTool(BaseTool):
    name = "echo"  # defines the URL: POST /api/tools/echo

    def execute(self, **kwargs):
        message = kwargs.get("message", "")
        return {"echo": message}

    def get_swagger_schema(self) -> dict:
        # We will fill this in Step 3
        ...
```

> `name` must be a **unique slug** — it becomes the URL path segment and the Swagger tag.

---

### Step 2 — Implement `execute`

`execute` receives the parsed request body as keyword arguments. If the client sends:

```json
{ "message": "Hello, world!" }
```

Then `execute` is called as:

```python
tool.execute(message="Hello, world!")
```

Return any JSON-serializable Python value (dict, list, string, etc.).

---

### Step 3 — Build the `get_swagger_schema()` dict

This is the most important step. The dict you return must be a valid **OpenAPI 3.x Path Item Object** fragment for a `POST` operation.

**Reading the spec:** The canonical reference is [https://spec.openapis.org/oas/v3.0.3#operation-object](https://spec.openapis.org/oas/v3.0.3#operation-object)

The top-level keys you will use most:

| OpenAPI key | Type | Purpose |
|---|---|---|
| `summary` | string | Short one-line description shown in the Swagger UI header. |
| `description` | string | Longer Markdown description shown when the endpoint is expanded. |
| `tags` | array of strings | Groups endpoints in the Swagger UI sidebar. |
| `requestBody` | object | Describes the JSON body the client must send. |
| `responses` | object | Maps HTTP status codes to their response descriptions. |

**Full example for `EchoTool`:**

```python
def get_swagger_schema(self) -> dict:
    return {
        "summary": "Echo a message",
        "description": "Returns the exact message sent by the client.",
        "tags": ["Utilities"],

        # requestBody describes what the client sends in the POST body
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["message"],        # fields the client MUST send
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The text to be echoed back.",
                                "example": "Hello, world!"
                            }
                        }
                    }
                }
            }
        },

        # responses maps each HTTP status code to a description + optional schema
        "responses": {
            "200": {
                "description": "Echo successful.",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "echo": {
                                    "type": "string",
                                    "example": "Hello, world!"
                                }
                            }
                        }
                    }
                }
            },
            "422": {
                "description": "Validation error — missing required field."
            }
        }
    }
```

> **Key insight:** the `requestBody.content["application/json"].schema` is a **JSON Schema** object. Every `property` must declare at minimum a `type` (`string`, `integer`, `boolean`, `array`, `object`). The `example` field is optional but makes the Swagger UI much friendlier.

---

### Step 4 — Register the tool in `toolbox.py`

Open `toolbox.py`, scroll to the bottom, and add your tool to the active list:

```python
ferramentas_ativas: list[BaseTool] = [
    ViaCepTool(),
    EchoTool(),   # ← add your new plugin here
]
```

Restart `uvicorn` and refresh `/docs`. Your new endpoint will appear automatically.

---

## OpenAPI Schema Reference

Quick reference for the most common JSON Schema types used inside `properties`:

| Python type | OpenAPI `type` | Optional extra |
|---|---|---|
| `str` | `"string"` | `"format": "date"`, `"minLength"`, `"maxLength"` |
| `int` | `"integer"` | `"minimum"`, `"maximum"` |
| `float` | `"number"` | `"format": "float"` |
| `bool` | `"boolean"` | — |
| `list` | `"array"` | `"items": { "type": "..." }` |
| `dict` | `"object"` | `"properties": { ... }` |

For a full reference, read the official documentation:

- **OpenAPI 3.0 Specification:** [https://spec.openapis.org/oas/v3.0.3](https://spec.openapis.org/oas/v3.0.3)
- **JSON Schema (used inside `schema` objects):** [https://json-schema.org/understanding-json-schema](https://json-schema.org/understanding-json-schema)
