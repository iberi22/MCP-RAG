"""CLI Agent LLM provider - calls headless agents like codex, gemini-cli, qwen-cli."""

from __future__ import annotations

import shutil
import subprocess
import sys
import re

from cerebro_python.domain.llm_provider import LLMProvider


class CLIAgentLLMClient(LLMProvider):
    """Adapter for local headless CLI agents."""

    def __init__(self, agent_binary: str = "codex") -> None:
        self._binary = agent_binary
        self._available = bool(shutil.which(agent_binary))

    @property
    def is_available(self) -> bool:
        return self._available

    def _run_cli(self, prompt: str) -> str:
        if not self._available:
            return ""
        try:
            result = subprocess.run(
                [self._binary, prompt],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except FileNotFoundError:
            # Binary disappeared between startup detection and invocation.
            self._available = False
            print(f"[cli-agent] binary not found: {self._binary}", file=sys.stderr)
            return ""
        except subprocess.TimeoutExpired:
            return ""
        except Exception:
            return ""

    def score_importance(self, text: str, context: str) -> float:
        prompt = f"Evaluador de importancia (0-10). Contexto: {context}. Memoria: {text}. Responde solo el numero."
        reply = self._run_cli(prompt)
        match = re.search(r"\d+", reply)
        return min(1.0, max(0.0, float(match.group(0)) / 10.0)) if match else 0.5

    def consolidate(self, texts: list[str]) -> str:
        prompt = "Consolida estos episodios en un solo hecho semantico:\n" + "\n".join(texts)
        return self._run_cli(prompt) or " | ".join(texts[:3])

    def rewrite_query(self, query: str) -> str:
        prompt = f"Expande esta consulta de busqueda RAG: {query}. Responde solo la expansion."
        return self._run_cli(prompt) or query

    def score_relevance(self, query: str, candidate_text: str) -> float:
        prompt = f"Relevancia (0-1). Consulta: {query}. Texto: {candidate_text[:500]}. Responde solo el numero."
        reply = self._run_cli(prompt)
        match = re.search(r"-?\d+(?:\.\d+)?", reply)
        return min(1.0, max(0.0, float(match.group(0)))) if match else 0.0
