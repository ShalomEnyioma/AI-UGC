#!/usr/bin/env bash
# Full pipeline: music -> frames -> MP4 (1920x1080, 60 fps, H.264 + AAC).
set -euo pipefail
cd "$(dirname "$0")"
WORK=${WORK:-./build}
mkdir -p "$WORK"

python3 music.py "$WORK/music.wav"
node render.mjs --out "$WORK/frames" --workers "${WORKERS:-4}" --sub "${SUB:-6}"

ffmpeg -y -v error -framerate 60 -i "$WORK/frames/f_%04d.png" -i "$WORK/music.wav" \
  -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -c:v libx264 -preset slow -crf 15 -profile:v high -level 4.2 -g 120 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 320k -ar 48000 -r 60 -t 15 -movflags +faststart showreel.mp4

ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration -of compact showreel.mp4
