#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

export TMPDIR="$project_root/tmp"
export BOOK_VERSION="${BOOK_VERSION:-пробная редактируемая сборка}"
export BOOK_BUILD_TIME="${BOOK_BUILD_TIME:-$(date '+%d.%m.%Y %H:%M:%S %Z')}"

output_dir="$project_root/tmp/editable"
output_name="probability-statistics-for-it-entrepreneurs"
docx_path="$output_dir/$output_name.docx"
processed_docx_path="$output_dir/$output_name.processed.docx"
odt_path="$output_dir/$output_name.odt"
with_odt=false

if [[ $# -gt 1 ]]; then
  echo "Использование: scripts/export-editable.sh [--with-odt]" >&2
  exit 2
fi

if [[ $# -eq 1 ]]; then
  if [[ "$1" != "--with-odt" ]]; then
    echo "Неизвестный параметр: $1" >&2
    echo "Использование: scripts/export-editable.sh [--with-odt]" >&2
    exit 2
  fi
  with_odt=true
fi

mkdir -p "$TMPDIR" "$output_dir"

quarto render --profile editable,part --to docx

if [[ ! -s "$docx_path" ]]; then
  echo "DOCX не создан: $docx_path" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 не найден: он необходим для постобработки DOCX" >&2
  exit 1
fi

find "$output_dir" -maxdepth 1 -type f -name "$output_name.processed.docx" -delete
python3 scripts/postprocess-editable-docx.py "$docx_path" "$processed_docx_path"
mv "$processed_docx_path" "$docx_path"

printf 'Создан:\n%s\n' "$docx_path"

if [[ "$with_odt" == true ]]; then
  if ! command -v soffice >/dev/null 2>&1; then
    echo "LibreOffice не найден: команда soffice недоступна" >&2
    exit 1
  fi

  lo_profile="$(mktemp -d "$TMPDIR/libreoffice-export.XXXXXX")"
  trap 'rm -rf -- "$lo_profile"' EXIT

  find "$output_dir" -maxdepth 1 -type f -name "$output_name.odt" -delete

  soffice --headless \
    -env:UserInstallation="file://$lo_profile" \
    --convert-to odt \
    --outdir "$output_dir" \
    "$docx_path"

  if [[ ! -s "$odt_path" ]]; then
    echo "ODT не создан: $odt_path" >&2
    exit 1
  fi

  printf 'Дополнительно создан:\n%s\n' "$odt_path"
fi
