#!/bin/bash
# Build A6300 GR III / GR IV + Fujifilm + Hasselblad X1D/X2D profiles from your local Lightroom install.
# Usage: ./build.sh [output_dir]
#   LR_PROFILES env var overrides the Lightroom CameraProfiles path.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LRP="${LR_PROFILES:-/Applications/Adobe Lightroom Classic/Adobe Lightroom Classic.app/Contents/Resources/CameraProfiles}"
OUT="$(mkdir -p "${1:-$HERE/build}" && cd "${1:-$HERE/build}" && pwd)"
[ -d "$LRP" ] || { echo "Lightroom CameraProfiles not found: $LRP" >&2; exit 1; }
cd "$OUT"
[ -d upstream ] || git clone --depth 1 https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation.git upstream
rm -rf ported assembled; mkdir -p ported assembled
cd upstream
echo "== 1/3 port GR III / GR IV looks onto the A6300 base"
python3 -I "$HERE/scripts/port.py" "$HERE/scripts" "$LRP" . ../ported "GR III"
python3 -I "$HERE/scripts/port.py" "$HERE/scripts" "$LRP" . ../ported "GR IV"
echo "== 2/3 Hasselblad X1D/X2D (fitted tables on the A6300 Adobe Standard)"
python3 -I "$HERE/scripts/assemble.py" "$LRP" "$HERE/data" ../assembled
cd "$OUT"
echo "== 3/3 package"
E="$OUT/export"; FJD="$E/A6300 Fujifilm Simulation"; HBD="$E/A6300 Hasselblad"
rm -rf "$E"; mkdir -p "$FJD/CameraProfiles" "$FJD/Settings/Fujifilm Simulation LUT" "$HBD/CameraProfiles" "$HBD/Settings/A6300 Hasselblad"
for M in "GR III" "GR IV"; do
  D="$E/A6300 $M Profiles"; mkdir -p "$D/CameraProfiles"; cp "ported/Sony ILCE-6300 $M "*.dcp "$D/CameraProfiles/"
  sed "s/{MODEL}/$M/g" "$HERE/templates/gr_install.txt" > "$D/安装说明.txt"
done
cp "upstream/Adobe Standard Linear Profile/Sony ILCE-6300 Adobe Standard Linear.dcp" "$FJD/CameraProfiles/"
cp upstream/"Fujifilm Simulation LUT"/*.xmp "$FJD/Settings/Fujifilm Simulation LUT/"
cp assembled/"Sony ILCE-6300 Hasselblad X"*.dcp "$HBD/CameraProfiles/"; cp "$HERE"/templates/hasselblad/*.xmp "$HBD/Settings/A6300 Hasselblad/"
cp "$HERE/templates/fuji_install.txt" "$FJD/安装说明.txt"; cp "$HERE/templates/hasselblad_install.txt" "$HBD/安装说明.txt"
python3 -I "$HERE/scripts/groups.py" "$OUT"
cd "$E"; for d in "A6300 GR III Profiles" "A6300 GR IV Profiles" "A6300 Fujifilm Simulation" "A6300 Hasselblad"; do zip -qr -X "$d.zip" "$d"; done
echo "Done: $E"
