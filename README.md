# Focus log

A small focus timer that logs every session into today's note in your Obsidian vault.
Works on a PC and on a phone (same Wi-Fi). Needs Python 3.10+ and nothing else.

## Run

```
python server.py
```

The terminal prints two addresses:

- `http://127.0.0.1:8765` on this PC
- `http://<your-pc-ip>:8765` on your phone (same Wi-Fi, allow Python through the Windows firewall for private networks)

Open the **Vault** section at the bottom of the page, enter the path to your Obsidian vault
(and an optional subfolder), and press Save. The path is stored in `config.json`, which is not committed.

## What it does

- Focus / break timer with 25, 50, 5, 10 minute presets and a custom length
- Logs `- HH:MM · Focus · 25 min · task` into `YYYY-MM-DD.md` under `## Focus log`
- Delete entries with the ✕ button
- **Time worked** page: total, today, last 7 days, and a per-day list

## Notes

- GitHub only stores the code. The app needs `server.py` running on your PC, because it writes into your vault,
  so it cannot run on GitHub Pages.
- Anyone on the same Wi-Fi can open the page while the server runs. Use a network you trust.
