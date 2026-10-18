#!/bin/bash
# Build A6300 GR III + Fujifilm + Hasselblad X1D profiles from your local Lightroom install.
# Usage: ./build.sh [output_dir]
#   LR_PROFILES env var overrides the Lightroom CameraProfiles path.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LRP="${LR_PROFILES:-/Applications/Adobe Lightroom Classic/Adobe Lightroom Classic.app/Contents/Resources/CameraProfiles}"
OUT="$(mkdir -p "${1:-$HERE/build}" && cd "${1:-$HERE/build}" && pwd)"
[ -d "$LRP" ] || { echo "Lightroom CameraProfiles not found: $LRP" >&2; exit 1; }
cd "$OUT"
[ -d upstream ] || git clone --depth 1 https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation.git upstream
W="$OUT/work"; mkdir -p "$W" ported final
cp "$HERE"/scripts/dcp.py "$HERE"/scripts/port.py "$W/"
cd upstream
echo "== 1/5 port GR III looks onto A6300 base";        python3 -I "$W/port.py" "$W" "$LRP" . ../ported
echo "== 2/5 RAW chart -> base colours (A6300/GR III)"; python3 -I "$HERE/scripts/rawbase.py" "$HERE/scripts" "$LRP" "$HERE/data/raw/patches_raw.json" "$W/base.json" "$HERE/data/raw/wheel_raw.json" "$W/wheel_base.json"
echo "== 3/5 fit A6300 -> GR III base correction";     python3 -I "$HERE/scripts/rawfit.py" "$HERE/scripts" "$W/base.json" "$W/wheel_base.json" gr3 "$W/model_gr3.json"
echo "== 4/5 build aligned GR III profiles";            python3 -I "$HERE/scripts/gr3/rawmatch.py" "$HERE/scripts" "$LRP" "$W/model_gr3.json" ../ported ../final
echo "== 5/5 Hasselblad X1D + Fuji base (fitted tables)"; python3 -I "$HERE/scripts/assemble.py" "$LRP" . "$HERE/data" ../assembled
cd "$OUT"
E="$OUT/export"; GRD="$E/A6300 GR III Profiles"; FJD="$E/A6300 Fujifilm Simulation"; HBD="$E/A6300 Hasselblad"
rm -rf "$E"; mkdir -p "$GRD/CameraProfiles" "$FJD/CameraProfiles" "$FJD/Settings/Fujifilm Simulation LUT" "$HBD/CameraProfiles" "$HBD/Settings/A6300 Hasselblad"
cp final/*.dcp "$GRD/CameraProfiles/"
cp "assembled/Sony ILCE-6300 Adobe Standard Linear.dcp" "$FJD/CameraProfiles/"
cp assembled/"Sony ILCE-6300 Hasselblad X1D"*.dcp "$HBD/CameraProfiles/"; cp "$HERE"/templates/hasselblad/*.xmp "$HBD/Settings/A6300 Hasselblad/"
cp upstream/"Fujifilm Simulation LUT"/*.xmp "$FJD/Settings/Fujifilm Simulation LUT/"
cp "$HERE/templates/gr3_install.txt" "$GRD/安装说明.txt"; cp "$HERE/templates/fuji_install.txt" "$FJD/安装说明.txt"; cp "$HERE/templates/hasselblad_install.txt" "$HBD/安装说明.txt"
python3 -I "$HERE/scripts/groups.py" "$OUT"
cd "$E" && zip -qr -X "A6300 GR III Profiles.zip" "A6300 GR III Profiles" && zip -qr -X "A6300 Fujifilm Simulation.zip" "A6300 Fujifilm Simulation" && zip -qr -X "A6300 Hasselblad.zip" "A6300 Hasselblad"
echo "Done: $E"
