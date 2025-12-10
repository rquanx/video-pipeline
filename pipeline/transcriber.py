from __future__ import annotations

"""转写模块，默认使用 vibe。"""

import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional

from .types import TranscribeResult
from .utils import run_subprocess, srt_to_txt


class VibeTranscriber:
    def __init__(self, model_path: str, subtitle_dir: Path, workers: int, extra_args: Optional[str] = None):
        self.model_path = model_path
        self.subtitle_dir = subtitle_dir
        self.workers = workers
        self.extra_args = shlex.split(extra_args) if extra_args else []

    def _build_command(self, source: Path, srt_path: Path) -> list[str]:
        base_cmd = [
            'vibe',
            '--model',
            self.model_path,
            '--file',
            str(source),
            '-l',
            'chinese',
            '--write',
            str(srt_path),
        ]
        if self.extra_args:
            return base_cmd + self.extra_args
        return base_cmd

    def _transcribe_one(self, source: Path) -> TranscribeResult:
        txt_path = self.subtitle_dir / f'{source.stem}.txt'
        if txt_path.exists():
            return TranscribeResult(source=source, success=True, message='txt exists, skipped')

        srt_path = self.subtitle_dir / f'{source.stem}.srt'
        if srt_path.exists():
            srt_to_txt(srt_path, txt_path)
            srt_path.unlink(missing_ok=True)
            return TranscribeResult(source=source, success=True, message='srt existed, converted')

        cmd = self._build_command(source, srt_path)
        proc = run_subprocess(cmd)
        if proc.returncode != 0:
            return TranscribeResult(source=source, success=False, message=proc.stderr.strip() or 'failed')

        if srt_path.exists():
            srt_to_txt(srt_path, txt_path)
            srt_path.unlink(missing_ok=True)
        else:
            return TranscribeResult(source=source, success=False, message='srt missing after transcription')

        return TranscribeResult(source=source, success=True, message='ok')

    def transcribe(self, sources: Iterable[Path]) -> List[TranscribeResult]:
        source_list = list(sources)
        if not source_list:
            return []
        worker_count = self.workers if self.workers and self.workers > 0 else min(32, len(source_list))
        results: List[TranscribeResult] = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(self._transcribe_one, src): src for src in source_list}
            for future in as_completed(futures):
                results.append(future.result())
        return results
