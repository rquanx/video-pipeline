# video-pipeline

CLI pipeline for downloading videos, transcribing with `vibe`, and summarizing subtitles via an external LLM command.

## Prerequisites
- Python 3.10+.
- `yt-dlp` installed and accessible in `PATH`.
- `vibe` CLI plus the model file (defaults to `~/Library/Application Support/github.com.thewh1teagle.vibe/ggml-large-v3-turbo.bin` on macOS; see `main.py` for other platforms).
- A cookies file for the video site if required by `yt-dlp` (defaults to `./cookies.txt`).

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick start
1) Prepare URLs in `input.txt` (one per line) or `input.json` (string array). See `input.example.txt`.
2) Prepare a prompt in `prompt/summary.md` (a default is provided).
3) Run the pipeline:
```bash
video-pipeline \
  --cookies-path ./cookies.txt \
  --video-path ./todo \
  --subtitle-path ./subtitle \
  --prompt-path ./prompt \
  --summary-path ./summary \
  --llm-command "your-llm-command"
```
Add `--skip-download`, `--skip-transcribe`, or `--skip-summary` to bypass stages. When `--llm-command` is omitted, the summarization step is skipped.

## Behavior
- URL loading: reads `input.txt` and/or `input.json` in `--input-dir`, plus `--url` flags; normalizes Bilibili watch-later links.
- Download: defaults to `yt-dlp` with cookies; parallel workers via `--download-workers`.
- Transcribe: uses `vibe` to produce `.srt`, converts to `.txt`, and deletes the `.srt`; parallel via `--transcribe-workers`.
- Summarize: feeds subtitle text and prompt to an external command; writes Markdown summaries to `--summary-path`; parallel via `--summary-workers`.
- Extensibility: custom downloader/transcriber can be provided as `module:ClassName` via `--downloader` / `--transcriber`.

## Project layout
- `main.py` – CLI entrypoint wiring the pipeline.
- `pipeline/` – download, transcribe, summarize modules and factories.
- `prompt/summary.md` – default summarization prompt (editable).
- `docs/` – design notes and future ideas.
- `summary/` – generated summaries (gitignored except for the placeholder).

## License
MIT. See `LICENSE`.
