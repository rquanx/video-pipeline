from __future__ import annotations

"""工具函数：目录创建、子进程执行、字幕清洗等。"""

import subprocess
from pathlib import Path
from typing import Optional


def ensure_dirs(*paths: Path) -> None:
    """确保目录存在。"""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def run_subprocess(
    command: list[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    input_text: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """运行子进程并捕获输出。"""
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input_text,
        check=False,
    )


def srt_to_txt(srt_path: Path, txt_path: Path) -> None:
    """将 srt 内容去除时间轴后转存为 txt。"""
    content = srt_path.read_text(encoding='utf-8')
    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
    lines: list[str] = []
    for block in blocks:
        parts = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.isdigit() or '-->' in stripped:
                continue
            parts.append(stripped)
        if parts:
            lines.append(' '.join(parts))
    txt_path.write_text('\n'.join(lines), encoding='utf-8')


def list_video_files(video_dir: Path) -> list[Path]:
    """列出支持后缀的视频文件。"""
    video_exts = {'.mp4', '.mkv', '.flv', '.mov', '.avi', '.webm'}
    return [p for p in video_dir.iterdir() if p.is_file() and p.suffix.lower() in video_exts]
