#!/bin/bash
# Build A6300 GR III + Fujifilm profiles from your local Lightroom install.
# Usage: ./build.sh [output_dir]
#   LR_PROFILES env var overrides the Lightroom CameraProfiles path.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LRP="${LR_PROFILES:-/Applications/Adobe Lightroom Classic/Adobe Lightroom Classic.app/Contents/Resources/CameraProfiles}"
OUT="$(mkdir -p "${1:-$HERE/build}" && cd "${1:-$HERE/build}" && pwd)"
[ -d "$LRP" ] || { echo "Lightroom CameraProfiles not found: $LRP" >&2; exit 1; }
cd "$OUT"
[ -d upstream ] || git clone --depth 1 https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation.git upstream
W="$OUT/work"; mkdir -p "$W/gr3" "$W/fuji" ported final final_fuji
cp "$HERE"/scripts/dcp.py "$HERE"/scripts/port.py "$W/gr3/"; cp "$HERE"/scripts/dcp.py "$HERE"/scripts/port.py "$W/fuji/"
cp "$HERE"/scripts/gr3/{fit.py,build3.py} "$HERE"/data/gr3_vs_a6300/patches.json "$W/gr3/"
cp "$HERE"/scripts/fuji/{fit.py,fit2d.py,buildfuji.py,groups.py} "$HERE"/data/xs20_vs_a6300/patches.json "$W/fuji/"
cd upstream
echo "== 1/4 port GR III looks onto A6300 base"; python3 -I "$W/gr3/port.py" "$W/gr3" "$LRP" . ../ported
echo "== 2/4 chart-calibrated GR III alignment";  python3 -I "$W/gr3/build3.py" "$W/gr3" "$LRP"
echo "== 2b   soft saturation compression";     python3 -I "$HERE/scripts/gr3/softsat.py" "$W/gr3" "$LRP" ../final ../final
echo "== 3/4 fit A6300 -> X-S20 alignment";       python3 -I "$W/fuji/fit2d.py" "$W/fuji" "$LRP"
echo "== 4/4 build aligned A6300 Linear base";    python3 -I "$W/fuji/buildfuji.py" "$W/fuji" "$LRP"
cd "$OUT"
E="$OUT/export"; GRD="$E/A6300 GR III Profiles"; FJD="$E/A6300 Fujifilm Simulation"
mkdir -p "$GRD/CameraProfiles" "$FJD/CameraProfiles" "$FJD/Settings/Fujifilm Simulation LUT"
cp final/*.dcp "$GRD/CameraProfiles/"; cp "final_fuji/Sony ILCE-6300 Adobe Standard Linear.dcp" "$FJD/CameraProfiles/"
cp upstream/"Fujifilm Simulation LUT"/*.xmp "$FJD/Settings/Fujifilm Simulation LUT/"
cp "$HERE/templates/gr3_install.txt" "$GRD/安装说明.txt"; cp "$HERE/templates/fuji_install.txt" "$FJD/安装说明.txt"
python3 -I "$W/fuji/groups.py" "$OUT"
cd "$E" && zip -qr -X "A6300 GR III Profiles.zip" "A6300 GR III Profiles" && zip -qr -X "A6300 Fujifilm Simulation.zip" "A6300 Fujifilm Simulation"
echo "Done: $E"
