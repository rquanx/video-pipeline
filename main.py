from __future__ import annotations

"""CLI 入口：按步骤调用下载、转写、摘要模块。"""

import argparse
import platform
from pathlib import Path
from typing import List, Optional

from pipeline.factory import create_downloader, create_transcriber
from pipeline.io_loader import load_urls
from pipeline.summarizer import CommandSummarizer, summarize_txt_files
from pipeline.types import Summarizer
from pipeline.utils import ensure_dirs, list_video_files


DEFAULT_INPUT_DIR = Path('.')
DEFAULT_COOKIES_PATH = Path('./cookies.txt')
DEFAULT_VIDEO_PATH = Path('./todo')
DEFAULT_SUBTITLE_PATH = Path('./subtitle')
DEFAULT_PROMPT_PATH = Path('./prompt')
DEFAULT_SUMMARY_PATH = Path('./summary')


def default_vibe_model_path() -> Path:
    """按平台推断 vibe 模型默认位置，兼容 Win/mac/linux。"""
    system = platform.system()
    if system == 'Windows':
        base = Path.home() / 'AppData' / 'Local' / 'github.com.thewh1teagle.vibe'
    elif system == 'Darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'github.com.thewh1teagle.vibe'
    else:
        base = Path.home() / '.local' / 'share' / 'github.com.thewh1teagle.vibe'
    return base / 'ggml-large-v3-turbo.bin'


DEFAULT_VIBE_MODEL_PATH = default_vibe_model_path()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Video pipeline tool')
    parser.add_argument('--input-dir', default=str(DEFAULT_INPUT_DIR))
    parser.add_argument('--cookies-path', default=str(DEFAULT_COOKIES_PATH))
    parser.add_argument('--video-path', default=str(DEFAULT_VIDEO_PATH))
    parser.add_argument('--vibe-model-path', default=str(DEFAULT_VIBE_MODEL_PATH))
    parser.add_argument('--subtitle-path', default=str(DEFAULT_SUBTITLE_PATH))
    parser.add_argument('--prompt-path', default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument('--summary-path', default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument('--downloader', default='yt-dlp', help='downloader kind or module:ClassName')
    parser.add_argument('--yt-dlp-args', default=None, help='extra args for yt-dlp')
    parser.add_argument('--transcriber', default='vibe', help='transcriber kind or module:ClassName')
    parser.add_argument('--vibe-args', default=None, help='extra args for vibe')
    parser.add_argument('--llm-command', default=None, help='external command for summarization')
    parser.add_argument('--download-workers', type=int, default=4)
    parser.add_argument('--transcribe-workers', type=int, default=2)
    parser.add_argument('--summary-workers', type=int, default=2)
    parser.add_argument('--skip-download', action='store_true')
    parser.add_argument('--skip-transcribe', action='store_true')
    parser.add_argument('--skip-summary', action='store_true')
    parser.add_argument('--url', action='append', help='url to process (can repeat)')
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_dir = Path(args.input_dir)
    cookies_path = Path(args.cookies_path)
    video_dir = Path(args.video_path)
    subtitle_dir = Path(args.subtitle_path)
    prompt_dir = Path(args.prompt_path)
    summary_dir = Path(args.summary_path)

    ensure_dirs(video_dir, subtitle_dir, prompt_dir, summary_dir)

    urls = load_urls(input_dir, args.url)
    if not urls:
        print('No URLs found. Provide --url or input.txt/json in input-dir.')
        return

    if not args.skip_download:
        downloader = create_downloader(
            kind=args.downloader,
            cookies_path=str(cookies_path),
            video_dir=str(video_dir),
            workers=args.download_workers,
            extra_args=args.yt_dlp_args,
        )
        print(f'Start downloading {len(urls)} url(s)...')
        download_results = downloader.download(urls)
        for res in download_results:
            status = 'ok' if res.success else 'fail'
            print(f'[download][{status}] {res.url} - {res.message}')
    else:
        print('Skipping download step.')

    video_files: List[Path] = list_video_files(video_dir)
    if not args.skip_transcribe:
        transcriber = create_transcriber(
            kind=args.transcriber,
            model_path=args.vibe_model_path,
            subtitle_dir=subtitle_dir,
            workers=args.transcribe_workers,
            extra_args=args.vibe_args,
        )
        if not video_files:
            print('No video files to transcribe.')
        else:
            print(f'Start transcribing {len(video_files)} file(s)...')
            transcribe_results = transcriber.transcribe(video_files)
            for res in transcribe_results:
                status = 'ok' if res.success else 'fail'
                print(f'[transcribe][{status}] {res.source.name} - {res.message}')
    else:
        print('Skipping transcribe step.')

    if not args.skip_summary:
        txt_files = sorted(subtitle_dir.glob('*.txt'))
        if not txt_files:
            print('No txt files for summarization.')
        else:
            summarizer: Optional[Summarizer]
            if args.llm_command:
                summarizer = CommandSummarizer(args.llm_command)
            else:
                summarizer = None
            print(f'Start summarizing {len(txt_files)} file(s)...')
            summary_results = summarize_txt_files(
                txt_files=txt_files,
                prompt_file=prompt_dir / 'summary.md',
                summary_dir=summary_dir,
                summarizer=summarizer,
                workers=args.summary_workers,
            )
            for res in summary_results:
                status = 'ok' if res.success else 'skip'
                print(f'[summary][{status}] {res.source.name} - {res.message}')
    else:
        print('Skipping summary step.')


if __name__ == '__main__':
    main()
