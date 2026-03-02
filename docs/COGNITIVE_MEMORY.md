# Sistema de Memoria Cognitiva (Cerebro Cognitivo)

Este sistema implementa una arquitectura de memoria jerárquica de 4 niveles, diseñada para simular el procesamiento de información del cerebro humano en agentes LLM.

## Arquitectura de 4 Niveles

| Nivel | Nombre | Descripción | Persistencia |
| :--- | :--- | :--- | :--- |
| **L0** | **Sensory Buffer** | Búfer crudo de la sesión actual. Sin procesamiento. | Volátil (Sesión) |
| **L1** | **Working Memory** | Información relevante para la tarea actual. Slots limitados. | Volátil |
| **L2** | **Episodic Memory** | Eventos y experiencias pasadas. Decaimiento temporal. | Persistente (SQLite) |
| **L3** | **Semantic Memory** | Hechos y conocimientos destilados. | Permanente (SQLite) |

## Fórmula de Puntuación Cognitiva

Cada fragmento de memoria posee un `cognitive_score` (0.0 a 1.0) calculado como:

```text
score = w_rec * recency + w_imp * importance + w_rel * relevance + w_freq * frequency
```

- **Recency**: Basado en la curva del olvido de Ebbinghaus ($e^{-\lambda t}$).
- **Importance**: Evaluada por el LLM (MiniMax) sobre el contenido.
- **Relevance**: Similitud vectorial con la consulta actual.
- **Frequency**: Número de accesos o menciones.

## Dinámica de la Memoria

1. **Promoción (L1 -> L2)**: Cuando una memoria en Working Memory alcanza el `PROMOTE_L1_THRESHOLD`, se persiste en el almacén Episódico.
2. **Consolidación (L2 -> L3)**: Cuando varios fragmentos episódicos relacionados superan el `CONSOLIDATE_THRESHOLD`, el LLM los sintetiza en un único hecho semántico permanente.
3. **Decaimiento (Olvido)**: Las memorias episódicas pierden puntuación con el tiempo. Si caen por debajo del `FORGET_THRESHOLD`, se eliminan o archivan.

## Configuración

Variables principales en `.env`:
- `RAG_COGNITIVE_ENABLED=true`
- `RAG_COGNITIVE_WM_SLOTS=20`
- `RAG_COGNITIVE_DECAY_LAMBDA=0.02` (Tasa de olvido por hora)
- `RAG_COGNITIVE_PROMOTE_L1_THRESHOLD=0.6`
- `RAG_COGNITIVE_CONSOLIDATE_THRESHOLD=0.75`
