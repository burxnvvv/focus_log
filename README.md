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

- **GitHub Pages / phone without the PC:** the page detects that there is no server and saves entries on the device
  (browser storage). The vault section is hidden, and the "Copy for Obsidian" button copies today's log as text.
  Stats work in this mode too. Entries stay in that one browser on that one phone.
- **With `python server.py`:** entries are written into the Obsidian vault on the PC instead.
- Anyone on the same Wi-Fi can open the page while the server runs. Use a network you trust.

## Add to the phone's home screen

Open the page on the phone, then Share -> Add to Home Screen (iPhone) or the browser menu -> Install app (Android). The app icon is `apple-touch-icon.png` / `icon-*.png`.
