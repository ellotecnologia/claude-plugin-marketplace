#!/usr/bin/env bash
#
# analisa_video.sh - Extrai frames-chave e transcreve o audio de um video
# (tipicamente videos de erro anexados em chamados). Roda 100% local/offline
# usando Docker (ffmpeg estatico + whisper.cpp).
#
# Uso:
#   analisa_video.sh <caminho_do_video> [dir_saida] [--lang pt] [--model small] [--intervalo 3]
#
# Saida: frames JPG + transcricao.txt em <dir_saida>; imprime a transcricao e o
# caminho dos frames para o agente ler (Read tool) os quadros.
#
# Os modelos whisper ficam num VOLUME NOMEADO do Docker (ello-whisper-models),
# nao num caminho do Windows -- evita o problema de file sharing do Docker Desktop
# (arquivos em algumas pastas do host nao aparecem dentro do container).
#
set -uo pipefail

# ---------- argumentos ----------
if [ $# -lt 1 ]; then
  echo "Uso: analisa_video.sh <video> [dir_saida] [--lang pt] [--model small] [--intervalo 3]" >&2
  exit 2
fi

VIDEO="$1"; shift
OUT_ARG=""
LANG="pt"
MODEL="small"     # base|small|medium (medium ~1.5GB, exige mais RAM no Docker)
INTERVALO="3"     # 1 frame a cada N segundos

while [ $# -gt 0 ]; do
  case "$1" in
    --lang)      LANG="$2"; shift 2 ;;
    --model)     MODEL="$2"; shift 2 ;;
    --intervalo) INTERVALO="$2"; shift 2 ;;
    --*)         echo "Flag desconhecida: $1" >&2; exit 2 ;;
    *)           OUT_ARG="$1"; shift ;;
  esac
done

# ---------- ambiente Docker (gotchas do Windows/Git Bash) ----------
# O credential helper docker-credential-desktop.exe precisa estar no PATH,
# senao 'docker pull' falha com "error getting credentials".
DOCKER_BIN="/c/Program Files/Docker/Docker/resources/bin"
[ -d "$DOCKER_BIN" ] && export PATH="$DOCKER_BIN:$PATH"
# Impede o Git Bash de converter os caminhos passados ao docker (-v, -i).
export MSYS_NO_PATHCONV=1

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: docker nao encontrado no PATH. Docker Desktop esta instalado?" >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "ERRO: o daemon do Docker nao respondeu. Abra o Docker Desktop e aguarde a baleia ficar estavel." >&2
  exit 1
fi

# ---------- caminhos (forma Windows com '/' p/ montar no Docker) ----------
VID_WIN=$(cygpath -m "$VIDEO")
VID_DIR_WIN=$(dirname "$VID_WIN")
VID_FILE=$(basename "$VID_WIN")
BASE="${VID_FILE%.*}"

if [ -n "$OUT_ARG" ]; then
  OUT_WIN=$(cygpath -m "$OUT_ARG")
else
  # sob ...\Temp\ (caminho que o Docker Desktop compartilha de forma confiavel)
  OUT_WIN="$(cygpath -m "${TEMP:-${LOCALAPPDATA:-$HOME}/Temp}")/ello-video/$BASE"
fi
OUT_UNIX=$(cygpath -u "$OUT_WIN")
mkdir -p "$OUT_UNIX/frames"

VOL_MODELS="ello-whisper-models"   # volume Docker p/ os modelos (nao depende de file sharing)

FFMPEG_IMG="mwader/static-ffmpeg:latest"
WHISPER_IMG="ghcr.io/ggml-org/whisper.cpp:main"

# ---------- garante imagens (puxa so na primeira vez) ----------
docker image inspect "$FFMPEG_IMG"  >/dev/null 2>&1 || { echo ">> baixando $FFMPEG_IMG ..."; docker pull "$FFMPEG_IMG"  >/dev/null; }
docker image inspect "$WHISPER_IMG" >/dev/null 2>&1 || { echo ">> baixando $WHISPER_IMG ..."; docker pull "$WHISPER_IMG" >/dev/null; }

# ---------- probe ----------
echo "=== INFO DO VIDEO ==="
docker run --rm -v "$VID_DIR_WIN:/in" --entrypoint /ffprobe "$FFMPEG_IMG" \
  -v error -show_entries format=duration:stream=codec_type,codec_name,width,height \
  -of default=noprint_wrappers=1 "/in/$VID_FILE" 2>&1

HAS_AUDIO=$(docker run --rm -v "$VID_DIR_WIN:/in" --entrypoint /ffprobe "$FFMPEG_IMG" \
  -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "/in/$VID_FILE" 2>/dev/null)

# ---------- frames (1 a cada N s; downscale se muito grande) ----------
echo
echo "=== EXTRAINDO FRAMES (1 a cada ${INTERVALO}s) ==="
docker run --rm -v "$VID_DIR_WIN:/in" -v "$OUT_WIN:/out" --entrypoint /ffmpeg "$FFMPEG_IMG" \
  -i "/in/$VID_FILE" -vf "fps=1/${INTERVALO},scale='min(720\,iw)':-2" -q:v 3 \
  "/out/frames/frame_%03d.jpg" -loglevel error -y 2>&1
NFRAMES=$(ls "$OUT_UNIX/frames" 2>/dev/null | grep -c '\.jpg$')
echo "Frames gerados: $NFRAMES em: $OUT_WIN/frames"

# ---------- audio + transcricao ----------
if [ -z "$HAS_AUDIO" ]; then
  echo
  echo "=== AUDIO: nenhuma trilha de audio no video (pulando transcricao) ==="
else
  echo
  echo "=== EXTRAINDO AUDIO + TRANSCREVENDO (lang=$LANG, model=$MODEL) ==="
  docker run --rm -v "$VID_DIR_WIN:/in" -v "$OUT_WIN:/out" --entrypoint /ffmpeg "$FFMPEG_IMG" \
    -i "/in/$VID_FILE" -vn -ar 16000 -ac 1 -c:a pcm_s16le "/out/audio.wav" -loglevel error -y 2>&1

  # modelo vive no volume nomeado; baixa so se ainda nao existir nele
  if ! docker run --rm -v "$VOL_MODELS:/models" "$WHISPER_IMG" "test -f /models/ggml-$MODEL.bin" >/dev/null 2>&1; then
    echo ">> baixando modelo whisper '$MODEL' no volume $VOL_MODELS ..."
    docker run --rm -v "$VOL_MODELS:/models" "$WHISPER_IMG" \
      "./models/download-ggml-model.sh $MODEL /models" >/dev/null 2>&1
  fi

  echo "--- TRANSCRICAO ---"
  docker run --rm -v "$OUT_WIN:/data" -v "$VOL_MODELS:/models" "$WHISPER_IMG" \
    "whisper-cli -m /models/ggml-$MODEL.bin -f /data/audio.wav -l $LANG -nt 2>/dev/null" \
    | tr -d '\r' | tee "$OUT_UNIX/transcricao.txt"
fi

echo
echo "=== PRONTO ==="
echo "Frames .....: $OUT_WIN/frames/frame_*.jpg  ($NFRAMES quadros)"
[ -n "$HAS_AUDIO" ] && echo "Transcricao : $OUT_WIN/transcricao.txt"
