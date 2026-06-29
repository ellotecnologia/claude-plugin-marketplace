---
name: transcribe
description: >
  Use this skill when the user asks to transcribe, analyze, "watch" or
  "listen to" a video — typically an error/playback video attached to a support
  ticket. Examples: "transcribe this video", "analyze the ticket's video", "what's
  in this video", "customer video showing the error", "extract the audio/subtitles
  from the video", "show me what appears on screen in this video".
version: 1.0.0
---

# Support Ticket Video Analysis

Does everything locally/offline via Docker (ffmpeg + whisper.cpp) — does not
send the video to any external service.

Extracts **key frames** (to "see" what's on screen) and transcribes the
**audio** (to "hear" the narration) from a video, running 100% locally via
Docker. Useful for diagnosing error videos attached to tickets: they're often
phone recordings filming the monitor (shaky footage) — in those cases **the
audio narration is usually the most valuable information**.

Pipeline: `ffprobe` (info) → `ffmpeg` (frames + 16kHz audio) → `whisper.cpp` (text).

## Prerequisites

- **Docker Desktop installed and running** (the stable whale icon in the tray). If
  not, open Docker Desktop and wait for the engine to start. To install:
  `winget install -e --id Docker.DockerDesktop`.
- The first run downloads the images (`mwader/static-ffmpeg` ~50MB,
  `ghcr.io/ggml-org/whisper.cpp` ~150MB) and the whisper model (`small` ~466MB).
  Everything is cached and reused afterward: the images in Docker and the model in
  a **named Docker volume** (`ello-whisper-models`).

## Step 1 — Video path

If the user hasn't provided the path, ask for it. The video may be in a local
folder or attached to the ticket (in that case, ask them to download it first).

## Step 2 — Run the script

Via the Bash tool, from the repository root:

```bash
.claude/skills/analyzing-chamado-videos/scripts/analisa_video.sh "<video_path>"
```

Optional flags: `--lang pt` (language; default pt), `--model small` (base|small|medium),
`--intervalo 3` (1 frame every N seconds), and a 2nd positional argument for the
output directory. The script prints: video info, frame count, **the transcription**,
and the output paths.

## Step 3 — Read the frames

Use the **Read tool** on the generated JPGs (`.../frames/frame_*.jpg`) to see the
screens: the user's steps, the app's screens, and the error message. When the video
is a phone filming the screen, the frames may be blurry — prioritize the transcription
and read the frames only to identify the screen/context.

## Step 4 — Synthesize

Combine audio + frames into a diagnosis: what the user did, where it broke, what the
error is. Since we know the app's codebase, **connect what appears on screen to the
point in the code** (screen, unit, query). If there's a ticket number, cross-reference
it with the ticket description (`ver_chamado` in TomTicket).

## Gotchas (already handled in the script — for reference)

- **`error getting credentials` on `docker pull`**: the helper
  `docker-credential-desktop.exe` needs to be on the PATH. The script does
  `export PATH="/c/Program Files/Docker/Docker/resources/bin:$PATH"`.
- **Git Bash converts the paths** passed to docker (`-v`, `-i`) and breaks them. The
  script uses `export MSYS_NO_PATHCONV=1` + `cygpath -m` (Windows path with `/`).
- **Docker Desktop file sharing (WSL2)**: files in some host folders (e.g.,
  `%LOCALAPPDATA%\...` outside `\Temp`) **don't show up** inside the container (the
  `-v` mount appears empty → whisper fails with "failed to open model"). That's why
  the model lives in a **named volume** (`ello-whisper-models`) and the output
  (frames/audio) goes under `...\Temp\ello-video\`.
- **`mwader/static-ffmpeg`**: the binaries live at the root — use
  `--entrypoint /ffprobe` and `--entrypoint /ffmpeg` (they're not on the image's PATH).
- **`whisper.cpp`**: the entrypoint is `bash -c`, so the command must be passed as
  **a single string** (`"whisper-cli -m ... -f ... -l pt -nt"`). Download the model
  with `./models/download-ggml-model.sh <model> /models`.
- **Docker RAM**: the `large` model needs ~10GB; with limited RAM use `base`/`small`.
- **`-nt`** (no-timestamps) + `2>/dev/null` leaves only clean text on stdout.

## Notes

- Runs offline: the video never leaves the machine (important for customer data).
- For timestamped subtitles (.srt) instead of running text, replace `-nt` with
  `-osrt -of /data/transcricao`.
