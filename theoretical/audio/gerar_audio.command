#!/bin/bash
# Gerador de audio do resumo da SLR — usa o comando `say` nativo do macOS.
# Duplo-clique neste arquivo no Finder para executar (precisa estar com permissão de
# execução: chmod +x gerar_audio.command).
#
# Voz padrao: Luciana (Portugues do Brasil). Para Portugues de Portugal, troque
# por "Joana" na linha VOICE abaixo.

set -e
cd "$(dirname "$0")"

VOICE="Luciana"          # Luciana = pt-BR;  Joana = pt-PT
RATE=185                 # palavras por minuto (180-200 e o ideal para narracao)
SCRIPT="roteiro_slr_pt-BR.txt"
OUT_AIFF="slr_resumo_pt-BR.aiff"
OUT_M4A="slr_resumo_pt-BR.m4a"
OUT_MP3="slr_resumo_pt-BR.mp3"

echo ""
echo "============================================================"
echo "  Gerando audio do resumo da SLR (voz: $VOICE, taxa: $RATE)"
echo "============================================================"
echo ""

# 1) Gera AIFF (formato nativo do `say`)
say -v "$VOICE" -r "$RATE" -f "$SCRIPT" -o "$OUT_AIFF"
echo "✓ AIFF gerado: $OUT_AIFF"

# 2) Converte para M4A (compactado, abre em qualquer app)
if command -v afconvert >/dev/null 2>&1; then
    afconvert -f m4af -d aac "$OUT_AIFF" "$OUT_M4A"
    echo "✓ M4A gerado: $OUT_M4A"
fi

# 3) Se ffmpeg estiver instalado, gera tambem MP3 (mais portavel)
if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -y -loglevel error -i "$OUT_AIFF" -codec:a libmp3lame -b:a 128k "$OUT_MP3"
    echo "✓ MP3 gerado: $OUT_MP3"
else
    echo "  (Para tambem gerar MP3, instale ffmpeg:  brew install ffmpeg)"
fi

echo ""
echo "Pronto! Audios disponiveis em: $(pwd)"
echo ""
read -p "Pressione Enter para fechar a janela..."
