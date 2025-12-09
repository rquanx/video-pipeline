from __future__ import annotations

"""下载模块，默认使用 yt-dlp。"""

import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional

from .types import DownloadResult
from .utils import run_subprocess


class YtDlpDownloader:
    def __init__(self, cookies_path: str, video_dir: str, workers: int, extra_args: Optional[str] = None):
        self.cookies_path = cookies_path
        self.video_dir = video_dir
        self.workers = workers
        self.extra_args = shlex.split(extra_args) if extra_args else []

    def _build_command(self, url: str) -> list[str]:
        base_cmd = [
            'yt-dlp',
            '--cookies',
            self.cookies_path,
            '-P',
            self.video_dir,
            url,
        ]
        if self.extra_args:
            return base_cmd[:-1] + self.extra_args + [url]
        return base_cmd

    def _download_one(self, url: str) -> DownloadResult:
        cmd = self._build_command(url)
        proc = run_subprocess(cmd)
        if proc.returncode == 0:
            return DownloadResult(url=url, success=True, message='ok')
        return DownloadResult(url=url, success=False, message=proc.stderr.strip() or 'failed')

    def download(self, urls: Iterable[str]) -> List[DownloadResult]:
        url_list = list(urls)
        if not url_list:
            return []
        worker_count = self.workers if self.workers and self.workers > 0 else min(32, len(url_list))
        results: List[DownloadResult] = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(self._download_one, url): url for url in url_list}
            for future in as_completed(futures):
                results.append(future.result())
        return results
