#!/bin/bash
# <xbar.title>Codex Usage Pace</xbar.title>
# <xbar.desc>Codex subscription usage versus the linear rolling-window budget</xbar.desc>
DIR="$(cd "$(dirname "$(readlink "$0" || echo "$0")")" && pwd)"
exec /usr/bin/python3 "$DIR/../codex_usage.py" --swiftbar
