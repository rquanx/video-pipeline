from __future__ import annotations

"""摘要模块，默认通过外部命令对接 LLM。"""

import importlib.util
import json
import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

import requests

from .types import SummaryResult, Summarizer
from .utils import ensure_dirs, run_subprocess


class NoOpSummarizer:
    def summarize_file(self, prompt: str, content: str, source: Path) -> str:
        raise RuntimeError("no summarizer configured")


class CommandSummarizer:
    def __init__(self, command: str):
        self.command = shlex.split(command)

    def summarize_file(self, prompt: str, content: str, source: Path) -> str:
        payload = build_prompt_payload(prompt, content, source)
        proc = run_subprocess(self.command, timeout=None, input_text=payload)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "summarizer failed")
        return proc.stdout.strip() or payload


class ResponsesAPISummarizer:
    """Summarizer backed by OpenAI-compatible /v1/responses API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 120,
        user_agent: str = "video-pipeline/0.1",
    ):
        self.endpoint = f"{base_url.rstrip('/')}/v1/responses"
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.user_agent = user_agent

    def summarize_file(self, prompt: str, content: str, source: Path) -> str:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": build_prompt_payload(prompt, content, source),
                        }
                    ],
                }
            ],
            "store": False,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }

        try:
            resp = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                stream=True,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"summary api request failed: {exc}") from exc

        with resp:
            if resp.status_code != 200:
                error_text = (resp.text or "").strip()
                if len(error_text) > 500:
                    error_text = f"{error_text[:500]}..."
                raise RuntimeError(
                    f"summary api error {resp.status_code}: {error_text or 'empty error body'}"
                )

            chunks: list[str] = []
            for raw_line in resp.iter_lines():
                event = self._parse_stream_line(raw_line)
                if event is None:
                    continue
                if event.get("type") == "response.completed" and chunks:
                    break
                chunk = self._extract_text_chunk(event)
                if chunk:
                    chunks.append(chunk)
                if self._is_done_event(event):
                    break

            summary = "".join(chunks).strip()
            if not summary:
                raise RuntimeError("summary api returned empty text")
            return summary

    @staticmethod
    def _parse_stream_line(raw_line: bytes) -> Optional[dict]:
        if not raw_line:
            return None
        line = raw_line.decode("utf-8", errors="ignore").strip()
        if not line:
            return None
        if line.startswith("event:"):
            return None
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line:
            return None
        if line == "[DONE]":
            return {"type": "done"}
        try:
            data = json.loads(line)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return {"type": "output_text.delta", "delta": line}

    @classmethod
    def _extract_text_chunk(cls, event: dict) -> str:
        event_type = event.get("type")

        if event_type in {"response.output_text.delta", "output_text.delta"}:
            delta = event.get("delta")
            return delta if isinstance(delta, str) else ""

        if event_type == "response.completed":
            response = event.get("response")
            if isinstance(response, dict):
                return cls._extract_text_from_response_obj(response)
            return ""

        output_text = event.get("output_text")
        if isinstance(output_text, str):
            return output_text

        if "output" in event:
            return cls._extract_text_from_response_obj(event)

        choices = event.get("choices")
        if isinstance(choices, list):
            chunks: list[str] = []
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta")
                if isinstance(delta, dict):
                    content = delta.get("content")
                    if isinstance(content, str):
                        chunks.append(content)
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                text = item.get("text")
                                if isinstance(text, str):
                                    chunks.append(text)
            return "".join(chunks)
        return ""

    @staticmethod
    def _extract_text_from_response_obj(obj: dict) -> str:
        output = obj.get("output")
        if not isinstance(output, list):
            return ""
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks)

    @staticmethod
    def _is_done_event(event: dict) -> bool:
        event_type = event.get("type")
        return event_type in {"done", "response.completed"}


def summarize_txt_files(
    txt_files: List[Path],
    prompt_file: Path,
    summary_dir: Path,
    summarizer: Optional[Summarizer],
    workers: int,
) -> List[SummaryResult]:
    if summarizer is None:
        return [
            SummaryResult(source=txt, success=False, message="skipped (no summarizer)")
            for txt in txt_files
        ]

    prompt = load_prompt_template(prompt_file)

    ensure_dirs(summary_dir)

    def worker(txt_file: Path) -> SummaryResult:
        try:
            content = txt_file.read_text(encoding="utf-8")
            summary = summarizer.summarize_file(prompt, content, txt_file)
            out_path = summary_dir / f"{txt_file.stem}.md"
            out_path.write_text(summary, encoding="utf-8")
            return SummaryResult(source=txt_file, success=True, message="ok")
        except Exception as exc:  # noqa: BLE001
            return SummaryResult(source=txt_file, success=False, message=str(exc))

    worker_count = workers if workers and workers > 0 else min(8, len(txt_files))
    results: List[SummaryResult] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(worker, path): path for path in txt_files}
        for future in as_completed(futures):
            results.append(future.result())
    return results


def build_prompt_payload(prompt: str, content: str, source: Path) -> str:
    base = prompt.strip()
    if not base:
        return f"# Source: {source.name}\n{content}"
    if "{content}" in base or "{source}" in base:
        return base.replace("{content}", content).replace("{source}", source.name)
    return f"{base}\n\n# Source: {source.name}\n{content}"


def load_prompt_template(prompt_file: Path) -> str:
    """Load prompt from summary.py:SUMMARY by default, fallback to .md file."""
    py_file = prompt_file.with_suffix(".py")
    if py_file.exists():
        try:
            spec = importlib.util.spec_from_file_location(
                "pipeline_prompt_summary", py_file
            )
            if spec is not None and spec.loader is not None:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                template = getattr(module, "SUMMARY", "")
                if isinstance(template, str) and template.strip():
                    return template
        except Exception:
            pass

    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return ""
