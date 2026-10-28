#!/usr/bin/env bash
set -euo pipefail
packet_dir="$(cd -- "$(dirname -- "$0")" && pwd -P)"
action="${1:-install}"
commit="__COMMIT__"
bundle_sha="__BUNDLE_SHA__"
packet_id="__PACKET_ID__"
install_root="${OPENT1D_INSTALL_ROOT:-${HOME}/.local/share/opent1d}"
checkout="${install_root}/${packet_id}/checkout"
tools="${install_root}/tools"
case "$action" in install|check|start) ;; *) echo "Choose install, check or start." >&2; exit 1;; esac
case "$(uname -s)" in Darwin|Linux) ;; *) echo "Use the Windows WSL launch files." >&2; exit 1;; esac
if [[ "$action" == install ]]; then
  for prerequisite in git curl; do
    if ! command -v "$prerequisite" >/dev/null 2>&1; then
      echo "Missing ${prerequisite}. On Ubuntu: sudo apt-get update && sudo apt-get install git curl ca-certificates" >&2
      echo "On macOS install Git and curl using the system's developer tools. Then try Install again." >&2
      exit 1
    fi
  done
  if ! command -v uv >/dev/null 2>&1 && [[ ! -x "$tools/uv" ]]; then
    installer="$(mktemp)"
    trap 'rm -f "$installer"' EXIT
    curl --proto '=https' --tlsv1.2 --fail --location https://astral.sh/uv/0.11.16/install.sh -o "$installer"
    UV_UNMANAGED_INSTALL="$tools" sh "$installer"
    rm -f "$installer"
    trap - EXIT
  fi
fi
export PATH="${tools}:${PATH}"
if ! command -v uv >/dev/null 2>&1; then echo "Install has not completed: uv is missing." >&2; exit 1; fi
if [[ "$action" == install && ! -e "$checkout" ]]; then
  actual_sha="$(uv run --no-project --python 3.12 python -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$packet_dir/source.bundle")"
  if [[ "$actual_sha" != "$bundle_sha" ]]; then echo "Source bundle changed. Request an intact packet." >&2; exit 1; fi
  mkdir -p -- "$(dirname -- "$checkout")"
  git clone --quiet -- "$packet_dir/source.bundle" "$checkout"
  git -C "$checkout" checkout --quiet --detach "$commit"
fi
if [[ ! -d "$checkout/.git" ]]; then echo "No installed checkout. Run Install first." >&2; exit 1; fi
if [[ "$(git -C "$checkout" rev-parse HEAD)" != "$commit" ]]; then echo "Installed checkout differs from this packet." >&2; exit 1; fi
cd -- "$checkout"
if [[ "$action" == install ]]; then
  uv sync --locked
  if [[ ! -d results/usability/packet ]]; then
    .venv/bin/python -m experiments.usability receive --packet "$packet_dir" --output results/usability/packet
  fi
  .venv/bin/python -m experiments.usability install --packet results/usability/packet
else
  if [[ ! -x .venv/bin/python ]]; then echo "Installation is incomplete. Run Install again." >&2; exit 1; fi
  arguments=("$action" --packet results/usability/packet)
  if [[ "$action" == start && "${OPENT1D_NO_BROWSER:-}" == 1 ]]; then arguments+=(--no-browser); fi
  .venv/bin/python -m experiments.usability "${arguments[@]}"
fi
