#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -u) -eq 0 || $(id -un) != ashin || $HOME != /home/ashin ]]; then
  printf '%s\n' 'Run as ashin with HOME=/home/ashin, without sudo.' >&2
  exit 1
fi
if [[ $(uname -m) != x86_64 ]] || ! [[ -r /etc/os-release ]] || ! /usr/bin/bash -c 'source /etc/os-release; [[ $ID == cachyos ]]'; then
  printf '%s\n' 'This bootstrap requires CachyOS x86-64.' >&2
  exit 1
fi
if ! command -v python3 >/dev/null; then
  for arg in "$@"; do
    if [[ $arg == --plan || $arg == --help || $arg == -h ]]; then
      printf '%s\n' 'Python is required to display the plan. Install python, then retry.' >&2
      exit 1
    fi
  done
  sudo pacman -Syu --needed python
fi
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ! -f $ROOT/scripts/bootstrap.py || ! -f $ROOT/manifests/capture.json || $(stat -c %u -- "$ROOT") != $(id -u) ]]; then
  for arg in "$@"; do
    if [[ $arg == --plan || $arg == --help || $arg == -h ]]; then
      printf '%s\n' 'Clone ashin-15/cachyos-bootstrap to inspect its offline plan.'
      exit 1
    fi
  done
  if ! command -v git >/dev/null; then
    sudo pacman -Syu --needed git
  fi
  ROOT=$HOME/Projects/cachyos-bootstrap
  if [[ -e $ROOT ]]; then
    if [[ ! -f $ROOT/scripts/bootstrap.py ]]; then
      printf '%s\n' "Existing destination is not a bootstrap checkout: $ROOT" >&2
      exit 1
    fi
  else
    mkdir -p -- "$(dirname -- "$ROOT")"
    git clone https://github.com/ashin-15/cachyos-bootstrap.git "$ROOT"
  fi
fi
exec python3 "$ROOT/scripts/bootstrap.py" "$@"
