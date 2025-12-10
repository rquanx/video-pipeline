from __future__ import annotations

"""工厂方法：按名称或模块路径创建下载/转写实现。"""

from importlib import import_module
from typing import Any, Type

from .downloader import YtDlpDownloader
from .transcriber import VibeTranscriber
from .types import Downloader, Transcriber


def _load_class(path: str) -> Type[Any]:
    """支持 module:Class 形式的动态加载。"""
    if ':' not in path:
        raise ValueError('custom loader must be in the form "module:ClassName"')
    module_name, class_name = path.split(':', 1)
    module = import_module(module_name)
    cls = getattr(module, class_name)
    return cls


def create_downloader(kind: str, **kwargs: Any) -> Downloader:
    """按 kind 创建 Downloader；支持内置或动态类路径。"""
    if ':' in kind:
        cls = _load_class(kind)
        return cls(**kwargs)
    if kind == 'yt-dlp':
        return YtDlpDownloader(**kwargs)
    raise ValueError(f'Unknown downloader kind: {kind}')


def create_transcriber(kind: str, **kwargs: Any) -> Transcriber:
    """按 kind 创建 Transcriber；支持内置或动态类路径。"""
    if ':' in kind:
        cls = _load_class(kind)
        return cls(**kwargs)
    if kind == 'vibe':
        return VibeTranscriber(**kwargs)
    raise ValueError(f'Unknown transcriber kind: {kind}')
