---
name: analyzing-chamado-videos
description: >
  Use esta skill quando o usuário pedir para transcrever, analisar, "assistir" ou
  "escutar" um vídeo — tipicamente um vídeo de erro/reprodução anexado em um chamado.
  Exemplos: "transcreve esse vídeo", "analisa o vídeo do chamado", "o que tem nesse
  vídeo", "vídeo do cliente mostrando o erro", "extrai o áudio/legenda do vídeo",
  "me mostra o que aparece na tela desse vídeo". Faz tudo local/offline via Docker
  (ffmpeg + whisper.cpp) — não envia o vídeo para nenhum serviço externo.
version: 1.0.0
---

# Análise de Vídeo de Chamado

Extrai **quadros-chave** (para "ver" o que aparece na tela) e **transcreve o áudio**
(para "ouvir" a narração) de um vídeo, rodando 100% local via Docker. Útil para
diagnosticar vídeos de erro anexados em chamados: muitas vezes são gravações de
celular filmando o monitor (tremidas) — nesses casos **a narração em áudio costuma
ser a informação mais valiosa**.

Pipeline: `ffprobe` (info) → `ffmpeg` (frames + áudio 16kHz) → `whisper.cpp` (texto).

## Pré-requisitos

- **Docker Desktop instalado e rodando** (a baleia estável na bandeja). Se não estiver,
  abrir o Docker Desktop e aguardar o engine subir. Sem instalar: `winget install -e --id Docker.DockerDesktop`.
- Primeira execução baixa as imagens (`mwader/static-ffmpeg` ~50MB,
  `ghcr.io/ggml-org/whisper.cpp` ~150MB) e o modelo whisper (`small` ~466MB). Tudo
  fica em cache e é reusado depois: as imagens no Docker e o modelo num **volume
  nomeado do Docker** (`ello-whisper-models`).

## Passo 1 — Caminho do vídeo

Se o usuário não informou o caminho, perguntar. O vídeo pode estar numa pasta local
ou anexado no chamado (nesse caso pedir para baixar primeiro).

## Passo 2 — Rodar o script

Pelo Bash tool, a partir da raiz do repositório:

```bash
.claude/skills/analyzing-chamado-videos/scripts/analisa_video.sh "<caminho_do_video>"
```

Opcionais: `--lang pt` (idioma; padrão pt), `--model small` (base|small|medium),
`--intervalo 3` (1 frame a cada N segundos), e um 2º argumento posicional para o
diretório de saída. O script imprime: info do vídeo, quantidade de frames, **a
transcrição** e os caminhos de saída.

## Passo 3 — Ler os frames

Use o **Read tool** nos JPGs gerados (`.../frames/frame_*.jpg`) para enxergar as telas:
passos do usuário, telas do Ello e a mensagem de erro. Quando o vídeo é celular
filmando a tela, os frames podem estar borrados — priorize a transcrição e leia os
frames só para identificar a tela/contexto.

## Passo 4 — Sintetizar

Juntar áudio + frames num diagnóstico: o que o usuário fez, onde quebrou, qual o erro.
Como conhecemos o código do Ello, **ligar o que aparece ao ponto no código** (tela,
unit, query). Se houver número de chamado, cruzar com a descrição dele (`ver_chamado`
no TomTicket).

## Gotchas (já resolvidos no script — referência)

- **`error getting credentials` no `docker pull`**: o helper `docker-credential-desktop.exe`
  precisa estar no PATH. O script faz `export PATH="/c/Program Files/Docker/Docker/resources/bin:$PATH"`.
- **Git Bash converte os caminhos** passados ao docker (`-v`, `-i`) e quebra. O script
  usa `export MSYS_NO_PATHCONV=1` + `cygpath -m` (caminho Windows com `/`).
- **File sharing do Docker Desktop (WSL2)**: arquivos em algumas pastas do host (ex.:
  `%LOCALAPPDATA%\...` fora de `\Temp`) **não aparecem** dentro do container (o `-v` monta
  a pasta vazia → whisper dá "failed to open model"). Por isso o modelo fica num **volume
  nomeado** (`ello-whisper-models`) e a saída (frames/áudio) sob `...\Temp\ello-video\`.
- **`mwader/static-ffmpeg`**: os binários ficam na raiz — usar `--entrypoint /ffprobe`
  e `--entrypoint /ffmpeg` (não estão no PATH da imagem).
- **`whisper.cpp`**: entrypoint é `bash -c`, então o comando vai como **uma string**
  (`"whisper-cli -m ... -f ... -l pt -nt"`). Baixar modelo com
  `./models/download-ggml-model.sh <model> /models`.
- **RAM do Docker**: modelo `large` precisa de ~10GB; com pouca RAM use `base`/`small`.
- **`-nt`** (no-timestamps) + `2>/dev/null` deixa só o texto limpo no stdout.

## Notas

- Roda offline: o vídeo não sai da máquina (importante para dados de cliente).
- Para legendas com tempo (.srt) em vez de texto corrido, trocar `-nt` por `-osrt -of /data/transcricao`.
