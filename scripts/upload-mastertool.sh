#!/usr/bin/env bash
# MASTERWORLD web paketini mastertool.download hesap servisine yükler (docs/masterworld.md §6 web-releases sözleşmesi).
# Kullanım: upload-mastertool.sh <sürüm> <masterworld-<sürüm>.tar.gz>
# Anahtar MASTERWORLD_RELEASE_KEY ortam değişkeninden okunur (GitHub secret); tanımlı değilse uyarı verip çıkar.
#
# Tek istek (paket ≤ 90 MB — Cloudflare tek istekte 100 MB kabul eder):
#   POST /api/mw/web-releases   multipart: version, package (tar.gz), sha256   → {ok, version, sha256, size}
# Büyük paket (isteğe bağlı parçalı uç; sunucuda varsa):
#   POST /api/mw/web-releases/<sürüm>/part   multipart: file, part, parts, sha256 (son parçada doğrulanır)
# Hatalar: 409 exists (aynı sürüm), 422 invalid_version / not_gzip / version_mismatch / bad_sha256 / too_large, 403.
set -euo pipefail

VERSION="${1:?sürüm}"
PKG="${2:?paket}"
VERSION="${VERSION#v}"
[ -f "$PKG" ] || { echo "::error::Paket yok: $PKG"; exit 1; }

API="${MT_API:-https://mastertool.download}/api/mw/web-releases"
PART_BYTES="${MT_PART_BYTES:-90000000}"     # test için küçültülebilir

if [ -z "${MASTERWORLD_RELEASE_KEY:-}" ]; then
  echo "::warning::MASTERWORLD_RELEASE_KEY tanımlı değil; mastertool.download'a yükleme atlandı."
  exit 0
fi

SHA=$(sha256sum "$PKG" | awk '{print $1}')
SIZE=$(stat -c %s "$PKG")
echo "Paket: $PKG ($SIZE bayt), sürüm $VERSION, sha256 $SHA"

if [ "$SIZE" -le "$PART_BYTES" ]; then
  CODE=$(curl -sS -o response.json -w '%{http_code}' -X POST "$API" -H "X-Release-Key: $MASTERWORLD_RELEASE_KEY" \
    -F "version=$VERSION" -F "package=@$PKG;type=application/gzip;filename=masterworld-$VERSION.tar.gz" -F "sha256=$SHA")
  echo "  HTTP $CODE $(cat response.json)" >&2
else
  # Parçalı: part 0..parts-1 sırayla; ara parça {ok, received}; son parça {ok, version, sha256, size}
  DIR=$(mktemp -d ./.mw-parts.XXXXXX); trap 'rm -rf "$DIR" response.json' EXIT
  split -b "$PART_BYTES" -d -a 3 "$PKG" "$DIR/part."
  PARTS=( "$DIR"/part.* ); TOTAL=${#PARTS[@]}; I=0; CODE=""
  for P in "${PARTS[@]}"; do
    CODE=$(curl -sS -o response.json -w '%{http_code}' -X POST "$API/$VERSION/part" -H "X-Release-Key: $MASTERWORLD_RELEASE_KEY" \
      -F "file=@$P;filename=masterworld-$VERSION.tar.gz" -F "part=$I" -F "parts=$TOTAL" -F "sha256=$SHA")
    echo "  parça $((I + 1))/$TOTAL → HTTP $CODE $(cat response.json)" >&2
    case "$CODE" in 200|201) ;; *) break ;; esac
    I=$((I + 1))
  done
fi
rm -f response.json

case "$CODE" in
  200|201) echo "mastertool.download: MASTERWORLD $VERSION yüklendi; sunucu hepgo-masterworld-deploy ile yayımlar." ;;
  409) echo "::notice::mastertool.download'da $VERSION zaten var (409); atlandı." ;;
  *) echo "::error::Yükleme başarısız (HTTP $CODE)."; exit 1 ;;
esac
