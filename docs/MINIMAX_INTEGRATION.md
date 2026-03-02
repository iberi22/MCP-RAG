# Integración con MiniMax (LLM & MCP)

Este proyecto utiliza el ecosistema de MiniMax para proporcionar inteligencia y datos frescos al RAG.

## 1. Cliente LLM (MiniMax Anthropic-Compatible)

El adaptador `MinimaxLLMClient` se comunica directamente con la API de MiniMax usando el formato compatible con Anthropic Messages.

- **Endpoint**: `https://api.minimax.io/anthropic/v1/messages`
- **Funciones**:
  - Scoring de importancia para memorias.
  - Consolidación de episodios en hechos semánticos.
  - Generación de respuestas fundamentadas (RAG).
- **Fallback**: Si la API no está disponible, el sistema usa comportamientos por defecto (scoring neutro y unión de texto simple) para no interrumpir el flujo.

## 2. MiniMax MCP (Web Search)

Utilizamos el MCP oficial `minimax-coding-plan-mcp` para dotar al RAG de capacidad de búsqueda web en tiempo real.

### Herramientas MCP
- `web_search`: Ejecuta búsquedas en internet y retorna fragmentos relevantes.
- `understand_image`: Permite analizar URLs de imágenes (para futura integración).

### Comandos CLI Web
- `rag-web-ingest -q "X"`: Busca en la web e ingesta automáticamente los resultados en el RAG.
- `rag-web-ask -q "X"`: Realiza el ciclo completo (Buscar -> Ingestar -> Responder) con un solo comando.

## Configuración (.env)

```bash
MINIMAX_API_KEY=tu_api_key_aqui
MINIMAX_API_HOST=https://api.minimax.io
MINIMAX_MODEL=MiniMax-M2.5
```
