from __future__ import annotations

"""公共类型与协议接口定义。"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Protocol


@dataclass
class DownloadResult:
    url: str
    success: bool
    message: str


@dataclass
class TranscribeResult:
    source: Path
    success: bool
    message: str


@dataclass
class SummaryResult:
    source: Path
    success: bool
    message: str


class Downloader(Protocol):
    def download(self, urls: Iterable[str]) -> List[DownloadResult]: ...


class Transcriber(Protocol):
    def transcribe(self, sources: Iterable[Path]) -> List[TranscribeResult]: ...


class Summarizer(Protocol):
    def summarize_file(self, prompt: str, content: str, source: Path) -> str: ...
