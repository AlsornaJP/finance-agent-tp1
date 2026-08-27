#!/bin/bash
# Reduz a gravação original para caber no limite de tamanho da entrega.
# Mantém 1920x1080 para preservar a legibilidade do texto em tela;
# a economia vem de baixar 60 fps para 15 (captura de tela é quase estática)
# e de comprimir o áudio de fala para mono 64 kbps.
set -euo pipefail

ORIGEM="${1:?uso: gerar_video.sh <arquivo-de-origem>}"
DESTINO="$(dirname "$0")/TP1_26E3_5_Joao_Pedro_Jacob_video.mp4"

ffmpeg -i "$ORIGEM" \
  -vf "fps=15" -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p \
  -c:a aac -b:a 64k -ac 1 -movflags +faststart \
  "$DESTINO" -y

echo "gerado: $DESTINO ($(( $(stat -c%s "$DESTINO") / 1024 / 1024 )) MB)"
