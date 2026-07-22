#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

export TMPDIR="$project_root/tmp"
export BOOK_VERSION="${BOOK_VERSION:-локальная проверка}"
export BOOK_BUILD_TIME="${BOOK_BUILD_TIME:-$(date '+%d.%m.%Y %H:%M:%S %Z')}"

mkdir -p "$TMPDIR/check"

usage() {
  cat <<'EOF'
Использование:
  scripts/check-book.sh quick <файл.qmd>
  scripts/check-book.sh format <файл.qmd> <html|pdf>
  scripts/check-book.sh part [html|pdf]
  scripts/check-book.sh full [html|pdf|all]

Режимы:
  quick   быстрая HTML-проверка одного раздела;
  format  проверка одного раздела в выбранном формате;
  part    сокращённая книжная сборка текущей части (сейчас — первой);
  full    полная сборка книги, по умолчанию HTML + PDF.
EOF
}

validate_format() {
  case "$1" in
    html|pdf) ;;
    *)
      echo "Допустимые форматы: html или pdf." >&2
      exit 2
      ;;
  esac
}

render_selection() {
  local input="$1"
  local format="$2"

  if [[ ! -e "$input" ]]; then
    echo "Не найден файл или каталог: $input" >&2
    exit 2
  fi

  validate_format "$format"
  quarto render "$input" --profile check --to "$format" --no-clean
}

mode="${1:-}"

case "$mode" in
  quick)
    input="${2:-}"
    if [[ -z "$input" ]]; then
      usage
      exit 2
    fi
    render_selection "$input" html
    ;;
  format)
    input="${2:-}"
    format="${3:-}"
    if [[ -z "$input" || -z "$format" ]]; then
      usage
      exit 2
    fi
    render_selection "$input" "$format"
    ;;
  part)
    format="${2:-html}"
    validate_format "$format"
    quarto render --profile part --to "$format"
    ;;
  full)
    format="${2:-all}"
    case "$format" in
      all) quarto render ;;
      html|pdf) quarto render --to "$format" ;;
      *)
        echo "Для полной сборки укажите html, pdf или all." >&2
        exit 2
        ;;
    esac
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "Неизвестный режим: $mode" >&2
    usage
    exit 2
    ;;
esac
