from __future__ import annotations

"""输入读取与 URL 规范化。"""

import json
from pathlib import Path
from typing import List, Optional


def normalize_url(url: str) -> str:
    """将稍后再看列表链接转成标准视频链接。"""
    if "list/watchlater" in url and "bvid=" in url:
        start = url.split("bvid=", 1)[1]
        bvid = start.split("&", 1)[0]
        return f"https://www.bilibili.com/video/{bvid}"
    return url


def load_urls(input_dir: Path, inline_urls: Optional[List[str]] = None) -> List[str]:
    """从 input.txt/json 与命令行拼合 URL 列表，去重并规范化。"""
    urls: List[str] = []
    seen = set()
    if inline_urls:
        for u in inline_urls:
            cleaned = normalize_url(u.strip())
            if cleaned and cleaned not in seen:
                urls.append(cleaned)
                seen.add(cleaned)

    txt_path = input_dir / "input.txt"
    if txt_path.exists():
        for line in txt_path.read_text(encoding="utf-8").splitlines():
            cleaned = normalize_url(line.strip())
            if cleaned and cleaned not in seen:
                urls.append(cleaned)
                seen.add(cleaned)

    json_path = input_dir / "input.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    cleaned = normalize_url(item.strip())
                    if cleaned and cleaned not in seen:
                        urls.append(cleaned)
                        seen.add(cleaned)
    return urls
