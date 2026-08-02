# codex-usage

A macOS SwiftBar/xbar tray icon for your Codex subscription limits. It compares
current usage with a linear budget for the live rolling window, so a high
percentage is only red when it is ahead of pace.

```
▼ 42%

Codex subscription (pro)
1-week: 42% used — resets Sun Aug 9 16:52
-- pace target now: 55.1% (-13.1 pts)
-- budget by end of today: 59.6%
-- projected at reset: ~76%
```

The script reads the signed-in Codex subscription session from
`~/.codex/auth.json`, then requests live usage. It never prints or writes the
token, and does not use an OpenAI API key. If the saved session expires, open
Codex or run `codex login`; the next refresh will work.

## Install in SwiftBar

```bash
brew install --cask swiftbar
chmod +x swiftbar/codex-usage.5m.sh codex_usage.py
# If SwiftBar already has a plugin directory, add this plugin to it rather than
# replacing the configured directory:
ln -s "$PWD/swiftbar/codex-usage.5m.sh" /path/to/swiftbar-plugins/
# For a new SwiftBar install only:
defaults write com.ameba.SwiftBar PluginDirectory -string "$PWD/swiftbar"
open -a SwiftBar
```

The plugin refreshes every five minutes.

- green `▼`: usage is more than 3 points under pace
- plain `●`: within 3 points of pace
- red `▲`: ahead of pace
- orange `⚠︎`: Codex is not signed in or the request failed

The tray uses the primary limit. Its menu includes every returned window,
including model-specific limits when your plan has them.

## Commands

```bash
python3 codex_usage.py
python3 codex_usage.py --swiftbar
python3 codex_usage.py --json
python3 -m unittest discover -s tests
```

For a separate Codex profile set `CODEX_USAGE_AUTH_FILE`. You may instead set
`CODEX_USAGE_TOKEN` and, optionally, `CODEX_USAGE_ACCOUNT_ID`.
