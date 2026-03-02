---
title: "Reglas y Flujos MCP para Agentes Codex"
doc_id: "knowledge/agents-rules"
version: "2025-10-14"
owners:
  - name: "Equipo Automations"
    role: "Orquestación de Agentes"
tags: [agents, operations, mcp, documentation-rules]
status: active
summary: "Guardrails, flujos y restricciones de documentación para agentes que operan en el workspace Codex."
---

# Reglas y Flujos MCP para Agentes Codex

## 🚨 REGLAS CRÍTICAS DE DOCUMENTACIÓN

### ❌ PROHIBIDO: Crear Nuevos Archivos .md

**Los agentes NO deben crear nuevos archivos .md en ninguna ubicación**. En su lugar:

1. **Para planning**: Actualizar `PLANNING.md` sección correspondiente
2. **Para tareas**: Actualizar `TASKS.md` con nueva entrada
3. **Para reportes**: Consolidar en Cerebro vía `memory_upsert`
4. **Para arquitectura**: Actualizar archivos existentes en `specs/architecture/`
5. **Para guías**: Actualizar archivos existentes en `specs/guides/`

### ✅ ESTRUCTURA DE DOCUMENTACIÓN AUTORIZADA

```
Raíz/ (Solo 7 archivos estratégicos)
├── README.md ✅ - Principal del proyecto
├── AGENTS.md ✅ - Este documento (reglas para agentes)
├── PLANNING.md ✅ - Roadmap y planificación estratégica
├── TASKS.md ✅ - Sprint tracking y tareas activas

specs/ (Documentación técnica organizada)
├── PROJECT_SPEC.md
├── architecture/
│   ├── cerebro-architecture.md
│   ├── cortex-multi-provider-architecture.md
│   ├── memory-api-contracts.md
│   └── MCP_ARCHITECTURE.md
├── constitution/
│   ├── PROJECT_CONSTITUTION.md
│   └── naming-conventions.md
├── guides/
│   ├── consuming-mcp-end-to-end.md
│   ├── credential-broker-integration.md
│   └── setup/
│       ├── mcp-access.md
│       └── NOTES_SETUP.md
├── implementation/
│   └── option-a-implementation-blueprint.md
├── development/
│   └── ARCHIVOS_GENERADOS.md
├── operations/
│   ├── cleanup_plan.md
│   └── sanitization_plan.md
├── reports/
│   ├── GATEWAY_SUCCESS_REPORT.md
│   └── UI_AND_MULTI_PROVIDER_COMPLETE.md
└── _templates/
    ├── feature.template.md
    ├── technical-plan.template.md
    └── doc.template.md
```

### 📝 PATRONES DE ACTUALIZACIÓN OBLIGATORIOS

#### Para PLANNING.md:
```markdown
## 🆕 [Fecha] - Nueva Iniciativa
- **Objetivo**: Descripción clara
- **Timeline**: Duración estimada
- **Owner**: Responsable
- **Priority**: High/Medium/Low
- **Dependencies**: Prerequisitos
```

#### Para TASKS.md:
```markdown
#### [ID]. [Título de Tarea]
**Priority:** High/Medium/Low
**Owner:** Team
**Target:** Objetivo específico
**Deadline:** YYYY-MM-DD

**Current Status:**
- ✅ Paso completado
- 🔄 Paso en progreso
- ⏳ Paso pendiente

**Blockers:** Lista de bloqueos si existen
```

#### Para Cerebro Memory:
```javascript
memory_upsert({
  sessionId: "session-id",
  collection: "project-knowledge|architecture-decisions|code-snippets",
  kind: "document|context|code_snippet",
  text: "Contenido consolidado...",
  meta: {
    category: "reports|analysis|decisions",
    key: "unique-identifier-YYYY-MM-DD",
    tags: ["relevant", "tags"],
    source: "nombre-archivo-original.md"
  }
})
```

## Contexto y Documentación

Este documento centraliza las normas operativas y los flujos de trabajo que rigen a los agentes MCP dentro del entorno Codex. Resume los principios, pasos y herramientas necesarias para coordinar tareas de automatización, manteniendo alineación con la memoria compartida y con los lineamientos de seguridad del proyecto.

### 📚 Referencias de Documentación Actualizada

**Documentos Principales (Raíz):**
- `README.md` - Punto de entrada principal del proyecto
- `PLANNING.md` - Roadmap estratégico y objetivos Q4 2025 → Q3 2026
- `TASKS.md` - Sprint tracking activo (Week 42) y backlog priorizado
- `AGENTS.md` - Este documento (reglas y flujos para agentes)

**Documentación Técnica (specs/):**
- `specs/guides/consuming-mcp-end-to-end.md` - Guía completa de integración MCP
- `specs/guides/credential-broker-integration.md` - Arquitectura de seguridad
- `specs/architecture/cerebro-architecture.md` - Componentes y deployment
- `specs/architecture/memory-api-contracts.md` - Contratos de memoria
- `specs/constitution/PROJECT_CONSTITUTION.md` - Principios del proyecto

**⚠️ IMPORTANTE**: Todos los reportes temporales han sido consolidados en Cerebro. Usar `memory_query` para recuperar información histórica.

## Principios Operativos Actualizados

- Este documento es la fuente de verdad para guardrails y objetivos de los agentes.
- **NUNCA crear nuevos archivos .md** - actualizar documentos existentes o usar Cerebro.
- Limita los cambios al workspace salvo que el usuario pida lo contrario.
- Favorece cambios mínimos, enfocados y con explicación del plan antes de modificaciones de gran alcance.
- Prioriza el uso de servicios Docker en lugar de binarios locales.
- Actualiza PLANNING.md y TASKS.md cuando cambie el comportamiento esperado.

## Bloque XML de Reglas Base

```xml
<mcp_cerebro_rules>
  <transport>
    - type: http_sse
    - sse_url: http://127.0.0.1:8001/sse (ACTUALIZADO desde 3001)
    - health_url: http://127.0.0.1:8001/health
    - fallback_stdio: Available for local development
  </transport>

  <documentation_rules>
    - NO CREATE new .md files anywhere in the project
    - UPDATE existing files: PLANNING.md, TASKS.md, specs/existing-files
    - USE memory_upsert for reports, analysis, temporary documents
    - CONSOLIDATE in Cerebro collections: project-knowledge, architecture-decisions, code-snippets
    - REFERENCE existing docs in specs/ for technical details
  </documentation_rules>

  <guiding_principles>
    - Treat memory as shared project context; query first, then write.
    - Prefer Docker services; do not spawn local binaries unless asked.
    - Keep changes minimal and scoped; update PLANNING.md when behavior changes.
    - Follow the approved documentation structure strictly.
  </guiding_principles>

  <memory_workflow>
    - Always start with: memory_query({ sessionId, query, top_k: 8 })
    - After new insights/decisions: memory_upsert({ sessionId, kind: "context", text, meta })
    - Store reusable code/commands: memory_upsert({ kind: "code_snippet" })
    - Collections: project-knowledge, code-snippets, debug-sessions, architecture-decisions
    - Use proper meta.category, meta.key, meta.tags for organization
  </memory_workflow>

  <agent_ops>
    - Use launch_agent / launch_qwen_agent for headless tasks when credentials exist.
    - Use credential_request → credential_configure_cognee when needed.
    - Tail long-lived logs via tail_logs.
    - Coordina rondas de conciencia vía `/consciousness/round` seleccionando proveedores según la carga disponible.
    - Consulta `/consciousness/providers` para revisar disponibilidad, modos de autenticación y cuotas activas.
  </agent_ops>

  <gateway>
    - base: http://127.0.0.1:8001 (ACTUALIZADO)
    - bus: redis (streams); prefer publish/request/reply patterns when coordinating tools.
    - storage: sqlite (RAG_REPOSITORY_ADAPTER=sqlite)
    - indexing: RAG_AUTO_INDEX_CODE=true enables background daemon syncing via rag-sync-repos.
    - chunking: RAG_CHUNKER_ADAPTER=ast (uses high-performance Rust tree-sitter binary).
    - embeddings: ollama (nomic-embed-text)
    - llm: MiniMax API directly accessed via urllib without SDK (MINIMAX_API_KEY, MINIMAX_MODEL=MiniMax-M2.5)
  </gateway>

  <security>
    - Do not store secrets in memory; reference IDs only.
    - Use credential_* tools for ephemeral tokens; call session_cleanup on exit.
    - All dependencies updated: 0 CVEs, FastAPI 0.115+, Redis 5.1.1+, Weaviate 4.7.0+.
  </security>

  <concurrency>
    - MCP_GEMINI_COUNT=4, MCP_QWEN_COUNT=1 (adjust via .env if needed).
    - 31 MCP tools available and operational.
  </concurrency>
</mcp_cerebro_rules>
```

## Flujos Operativos Actualizados

### Flujo Estándar

1. **Consultar memoria**: `memory_query({ sessionId, query: "context for <task>" })` para recuperar decisiones previas.
2. **Leer documentación existente**: Revisar `README.md`, `PLANNING.md`, `TASKS.md` y archivos relevantes en `specs/`.
3. **Proponer plan**: Breve y contextualizado, sin crear nuevos archivos .md.
4. **Implementar cambios**: Enfocados y mínimos.
5. **Actualizar documentación**: PLANNING.md para roadmap, TASKS.md para tareas, memory_upsert para reportes.
6. **Validar**: Comandos específicos y health checks.
7. **Consolidar**: Resumir en memoria de Cerebro si es conocimiento reutilizable.

### Flujo Consciente de Memoria

1. **Consultar memoria**: `memory_query({ sessionId, query: "initial context for <task>" })` para recuperar decisiones previas.
2. **Inspeccionar el código**: Analizar el repositorio con herramientas de búsqueda (`grep_search`, lectura dirigida) cuando falte contexto.
3. **Revisar documentación**: Consultar structure autorizada en raíz y `specs/`.
4. **Actualizar memoria**: Persistir hallazgos con `memory_upsert({ sessionId, kind: "context", text, meta })`.
5. **Actualizar docs**: PLANNING.md para cambios estratégicos, TASKS.md para tareas operativas.
6. **Implementar y validar**: Ejecutar los cambios y comprobar resultados.
7. **Cerrar la sesión**: Registrar snippets reutilizables en `code-snippets` collection.

### Flujo de Documentación (NUEVO)

**❌ NUNCA CREAR .md nuevos**. En su lugar:

1. **Para planificación estratégica**: Actualizar `PLANNING.md`
   ```markdown
   ## 🆕 [YYYY-MM-DD] - Nueva Iniciativa
   - **Objetivo**: Descripción clara
   - **Timeline**: Duración estimada
   - **Owner**: Responsable
   - **Priority**: High/Medium/Low
   ```

2. **Para tareas operativas**: Actualizar `TASKS.md`
   ```markdown
   #### [ID]. [Título de Tarea]
   **Priority:** High/Medium/Low
   **Owner:** Team
   **Current Status:**
   - ✅ Completado
   - 🔄 En progreso
   - ⏳ Pendiente
   ```

3. **Para reportes/análisis**: Usar `memory_upsert`
   ```javascript
   memory_upsert({
     sessionId: "session-id",
     collection: "project-knowledge",
     kind: "document",
     text: "Contenido del reporte...",
     meta: {
       category: "reports",
       key: "report-name-YYYY-MM-DD",
       tags: ["analysis", "results"]
     }
   })
   ```

4. **Para arquitectura**: Actualizar archivos existentes en `specs/architecture/`
5. **Para guías técnicas**: Actualizar archivos en `specs/guides/`

## Operaciones de Conciencia Multiproveedor (Actualizado)

- **Objetivo**: distribuir la carga cognitiva entre OpenAI, ChatGPT Plus, Google Cloud Code, OpenRouter, Qwen, Codex CLI y Chutes AI.
- **Endpoints actualizados**:
  - `GET http://localhost:8001/consciousness/providers` para conocer disponibilidad, modos de autenticación y métricas.
  - `POST http://localhost:8001/consciousness/round` con payload:

    ```json
    {
      "sessionId": "<sid>",
      "objective": "Resumir backlog de features",
      "projectId": "cerebro",
      "providers": ["openai", "open_router", "codex_cli"],
      "inputs": ["PLANNING.md", "TASKS.md", "SYSTEM_STATUS.md"],
      "providerCredentials": {"openai": "<credential-id>"},
      "metadata": {"priority": "high"}
    }
    ```

- **Selección**: el registro aplica LRU y balanceo por éxitos/fallos respetando `maxProviders`.
- **Credenciales**: `providerCredentials` fija `credential_id`; si falta, el broker usa la credencial activa asociada al `sessionId`.
- **Resultados**: Las rondas se guardan como `kind=analysis` en `consciousness-rounds` y se consultan vía `memory_query`.

## Herramientas MCP Disponibles

El servidor Python MCP (`cerebro_python/tools/`) expone:

- `memory_upsert` y `memory_query` para memoria semántica.
- `credential_request`, `credential_status`, `credential_revoke`, `credential_configure_cognee`, `credential_health`, `session_cleanup` para credenciales efímeras.
- `analyze_documentation_md`, `analyze_project_structure`, `generate_comprehensive_recommendations` para análisis automatizado.
- `intelligent_onboarding`, `query_project_knowledge`, `validate_memory_robustness` para ingestión y diagnóstico de conocimiento.

Configuraciones clave:

- `MCP_COGNEE_BASE` apunta a `http://127.0.0.1:8001` (o `http://cerebro_python:8001` en Docker).
- Priorizar transporte HTTP/SSE; usar STDIO local solo cuando el cliente no soporte SSE.

## Seguridad y Gestión de Credenciales

- No almacenar secretos ni tokens explícitos en la memoria; usar solo referencias.
- Gestionar accesos con la familia `credential_*` y finalizar con `session_cleanup`.
- Revisar la salud del gateway con `credential_health` y supervisar logs prolongados con `tail_logs`.

## Comandos de Referencia

- Levantar todo el stack: `docker compose up -d --build`.
- Revisar salud del gateway: `curl http://localhost:8001/health`.
- Listar proveedores disponibles: `curl http://localhost:8001/consciousness/providers`.
- Ejecutar gateway Python local: `cd cerebro_python && python run_gateway.py`.
- Correr pruebas unificadas: `cd cerebro_python && python run_tests.py`.
- Reiniciar solo el gateway Python: `docker compose up -d --build cerebro_python`.

## Convenciones de Conocimiento

### Regla Global de Memoria

```xml
<memory_rules>
  <guiding_principles>
    - Treat memory as a first-class artifact to accelerate future tasks.
    - Never store secrets or real credentials; only references or metadata.
    - Prefer concise, structured entries with clear keys and timestamps.
    - Use semantic search before creating duplicate entries.
  </guiding_principles>

  <collections>
    - development-tools
    - project-knowledge
    - code-snippets
    - debug-sessions
    - architecture-decisions
  </collections>

  <key_convention>
    format = "{category}-{subcat}-{timestamp}"; example = "tool-mcp-memory_upsert-20250901"
  </key_convention>

  <when_to_write>
    - After resolving bugs or incidents (root cause, fix, PR/commit refs).
    - After discovering repo conventions, paths, configs (e.g., MCP_COGNEE_BASE).
    - When producing reusable snippets or workflows.
  </when_to_write>

  <how_to_write>
    - Prefer: memory_upsert with payload { sessionId, kind, text, meta }.
    - kind: "document" para artefactos extensos; "context" para notas cortas.
    - meta debe incluir: collection, key, tags, file_paths, related_tools.
  </how_to_write>

  <how_to_query>
    - Use memory_query con { sessionId, query, top_k, tenantId? }.
    - Combine resultados con el contexto actual citando colección y claves.
  </how_to_query>

  <maintenance>
    - Purgar entradas obsoletas y deduplicar claves.
    - Ejecutar session_cleanup al cerrar sesiones.
  </maintenance>

  <security>
    - No subir API keys o tokens en claro; usar IDs o referencias.
    - Respetar las políticas de retención del proyecto.
  </security>
</memory_rules>
```

### Guía de Prompts para Agentes de Código

```xml
<code_editing_rules>
  <be_precise>
    - Resolve ambiguities early; avoid conflicting instructions.
    - Quote exact paths/functions when referring to code (e.g., `cerebro_python/tools/memory_validator.py`).
  </be_precise>

  <reasoning_effort>
    - Default = medium. Use high for architecture/bug root-cause; low for trivial edits.
  </reasoning_effort>

  <structure_with_xml>
    - Use XML-like sections for plans, memory, and workflows as shown here.
  </structure_with_xml>

  <language_tone>
    - Avoid overly firm language; be concise and actionable.
  </language_tone>

  <self_reflection>
    - Draft a short rubric before large builds; validate against it post-change.
  </self_reflection>

  <eagerness_control>
    - Parallelize safe reads/searches; avoid unnecessary external calls.
    - Stop to confirm only when decisions are destructive or ambiguous.
  </eagerness_control>
</code_editing_rules>
```

### Regla Global de Memoria

```xml
<memory_rules>
  <guiding_principles>
    - Treat memory as a first-class artifact to accelerate future tasks.
    - Never store secrets or real credentials; only references or metadata.
    - Prefer concise, structured entries with clear keys and timestamps.
    - Use semantic search before creating duplicate entries.
  </guiding_principles>

  <collections>
    - development-tools
    - project-knowledge
    - code-snippets
    - debug-sessions
    - architecture-decisions
  </collections>

  <key_convention>
    format = "{category}-{subcat}-{timestamp}"; example = "tool-mcp-memory_upsert-20250901"
  </key_convention>

  <when_to_write>
    - After resolving bugs or incidents (root cause, fix, PR/commit refs).
    - After discovering repo conventions, paths, configs (e.g., MCP_COGNEE_BASE).
    - When producing reusable snippets or workflows.
  </when_to_write>

  <how_to_write>
    - Prefer: memory_upsert with payload { sessionId, kind, text, meta }.
    - kind: "document" para artefactos extensos; "context" para notas cortas.
    - meta debe incluir: collection, key, tags, file_paths, related_tools.
  </how_to_write>

  <how_to_query>
    - Use memory_query con { sessionId, query, top_k, tenantId? }.
    - Combine resultados con el contexto actual citando colección y claves.
  </how_to_query>

  <maintenance>
    - Purgar entradas obsoletas y deduplicar claves.
    - Ejecutar session_cleanup al cerrar sesiones.
  </maintenance>

  <security>
    - No subir API keys o tokens en claro; usar IDs o referencias.
    - Respetar las políticas de retención del proyecto.
  </security>
</memory_rules>
```

### Forma de las Peticiones

- `memory_upsert` requiere `text` (o `content`) y acepta `sessionId`, `agentId`, `kind`, `meta` para colecciones y claves.
- `memory_query` solicita `sessionId`, `query` y puede incluir `top_k` o `tenantId`.

### Workflow de Base de Conocimiento

1. Mantener documentos bajo `knowledge/` utilizando `knowledge/_templates/doc.template.md`.
2. Registrar frontmatter con `title`, `doc_id`, `version`, `owners`, `tags`, `status` y `summary`.
3. Sincronizar cambios con `spec_sync` (`collection=project-spec`, `scope=project` por defecto).
4. Consultar la memoria con filtros por `collection`, `doc_id` y `tags`.

## Guía de Prompts para Agentes de Código

```xml
<code_editing_rules>
  <be_precise>
    - Resolve ambiguities early; avoid conflicting instructions.
    - Quote exact paths/functions when referring to code (e.g., `cerebro_python/tools/memory_validator.py`).
  </be_precise>

  <reasoning_effort>
    - Default = medium. Use high for architecture/bug root-cause; low for trivial edits.
  </reasoning_effort>

  <structure_with_xml>
    - Use XML-like sections for plans, memory, and workflows as shown here.
  </structure_with_xml>

  <language_tone>
    - Avoid overly firm language; be concise and actionable.
  </language_tone>

  <self_reflection>
    - Draft a short rubric before large builds; validate against it post-change.
  </self_reflection>

  <eagerness_control>
    - Parallelize safe reads/searches; avoid unnecessary external calls.
    - Stop to confirm only when decisions are destructive or ambiguous.
  </eagerness_control>
</code_editing_rules>
```

## Flujo Operativo Detallado

1. Validar que el Gateway Python esté activo: `python_gateway_start` respeta `MCP_COGNEE_BASE`.
2. Solicitar credenciales con `credential_request` y configurarlas mediante `credential_configure_cognee` cuando sea necesario.
3. Persistir conocimiento relevante con `memory_upsert` (incluyendo `meta.collection` y `key`).
4. Recuperar información histórica con `memory_query` antes de cada intervención.
5. Cerrar sesiones ejecutando `session_cleanup` y auditando con `credential_status` / `credential_health`.

Arquitectura de referencia: un puente MCP en Node canaliza peticiones al Gateway Python (FastAPI) que delega en Cognee.
