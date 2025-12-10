from __future__ import annotations

"""摘要模块，默认通过外部命令对接 LLM。"""

import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from .types import SummaryResult, Summarizer
from .utils import ensure_dirs, run_subprocess


class NoOpSummarizer:
    def summarize_file(self, prompt: str, content: str, source: Path) -> str:
        raise RuntimeError("no summarizer configured")


class CommandSummarizer:
    def __init__(self, command: str):
        self.command = shlex.split(command)

    def summarize_file(self, prompt: str, content: str, source: Path) -> str:
        payload = f"{prompt}\n\n# Source: {source.name}\n{content}"
        proc = run_subprocess(self.command, timeout=None, input_text=payload)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "summarizer failed")
        return proc.stdout.strip() or payload


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

    prompt = ""
    if prompt_file.exists():
        prompt = prompt_file.read_text(encoding="utf-8")

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
