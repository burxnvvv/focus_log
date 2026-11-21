import json
import re
import socket
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "0.0.0.0"  # 0.0.0.0 = reachable from your phone on the same Wi-Fi
PORT = 8765
ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT
CONFIG_PATH = ROOT / "config.json"
MAX_BODY = 64 * 1024
MODES = {"focus": "Focus", "break": "Break"}
SECTION = "## Focus log"
ENTRY = re.compile(r"^- \d{2}:\d{2} \u00b7 ")
DETAIL = re.compile(r"^- \d{2}:\d{2} \u00b7 (Focus|Break) \u00b7 (\d+) min")
STATIC = {
    "/logo.png": "image/png",
    "/apple-touch-icon.png": "image/png",
    "/icon-192.png": "image/png",
    "/icon-512.png": "image/png",
    "/favicon-32.png": "image/png",
    "/manifest.webmanifest": "application/manifest+json",
}
NOTE_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def load_config() -> dict:
    config = {
        "vaultPath": str(Path.home() / "Documents" / "Obsidian Vault"),
        "noteFolder": "",
    }
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config["vaultPath"] = str(data.get("vaultPath") or config["vaultPath"])
                config["noteFolder"] = str(data.get("noteFolder") or "")
        except (OSError, json.JSONDecodeError):
            pass
    return config


def save_config(payload: dict) -> dict:
    vault = str(payload.get("vaultPath") or "").strip().strip('"')
    folder = str(payload.get("noteFolder") or "").strip().strip("/\\")
    if not vault:
        raise ValueError("Vault path is required")
    if not Path(vault).is_dir():
        raise ValueError("Vault folder does not exist")
    if ".." in Path(folder).parts:
        raise ValueError("Subfolder must stay inside the vault")
    config = {"vaultPath": vault, "noteFolder": folder}
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def note_path(config: dict, day: str) -> Path:
    folder = Path(config["vaultPath"])
    if config["noteFolder"]:
        folder = folder / config["noteFolder"]
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{day}.md"


def clean_label(label: str) -> str:
    return " ".join(str(label).split())[:160]


def entry_indexes(lines: list[str]) -> list[int]:
    return [i for i, item in enumerate(lines) if ENTRY.match(item)]


def today_payload(config: dict | None = None) -> dict:
    config = config or load_config()
    day = datetime.now().strftime("%Y-%m-%d")
    path = note_path(config, day)
    lines = []
    if path.exists():
        text = path.read_text(encoding="utf-8").splitlines()
        lines = [text[i][2:].strip() for i in entry_indexes(text)]
    return {
        "date": day,
        "notePath": str(path),
        "lines": lines,
        "vaultPath": config["vaultPath"],
        "noteFolder": config["noteFolder"],
    }


def log_session(payload: dict) -> dict:
    mode = str(payload.get("mode") or "")
    if mode not in MODES:
        raise ValueError("Mode must be focus or break")
    try:
        minutes = int(payload.get("minutes"))
    except (TypeError, ValueError):
        raise ValueError("Minutes must be a whole number") from None
    if minutes < 1 or minutes > 180:
        raise ValueError("Minutes must be between 1 and 180")
    label = clean_label(payload.get("label") or "")
    config = load_config()
    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    line = f"- {now.strftime('%H:%M')} \u00b7 {MODES[mode]} \u00b7 {minutes} min"
    if label:
        line += f" \u00b7 {label}"
    path = note_path(config, day)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else [f"# {day}"]
    found = entry_indexes(lines)
    if found:
        lines.insert(found[-1] + 1, line)
    else:
        while lines and lines[-1].strip() == "":
            lines.pop()
        lines += ["", SECTION, line]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = today_payload(config)
    result["ok"] = True
    result["line"] = line[2:]
    return result


def delete_session(payload: dict) -> dict:
    try:
        index = int(payload.get("index"))
    except (TypeError, ValueError):
        raise ValueError("Bad entry index") from None
    config = load_config()
    path = note_path(config, datetime.now().strftime("%Y-%m-%d"))
    if not path.exists():
        raise ValueError("Nothing to delete")
    lines = path.read_text(encoding="utf-8").splitlines()
    found = entry_indexes(lines)
    if index < 0 or index >= len(found):
        raise ValueError("Entry not found")
    del lines[found[index]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = today_payload(config)
    result["ok"] = True
    return result


def stats_payload() -> dict:
    config = load_config()
    folder = note_path(config, "x").parent
    days = []
    for file in sorted(folder.glob("*.md"), reverse=True):
        if not NOTE_NAME.match(file.name):
            continue
        focus = brk = sessions = 0
        for item in file.read_text(encoding="utf-8").splitlines():
            match = DETAIL.match(item)
            if not match:
                continue
            if match.group(1) == "Focus":
                focus += int(match.group(2))
                sessions += 1
            else:
                brk += int(match.group(2))
        if focus or brk:
            days.append({"date": file.stem, "focusMin": focus, "breakMin": brk, "sessions": sessions})
    today = datetime.now().date()
    week_start = (today - timedelta(days=6)).isoformat()
    return {
        "todayMin": sum(d["focusMin"] for d in days if d["date"] == today.isoformat()),
        "weekMin": sum(d["focusMin"] for d in days if d["date"] >= week_start),
        "totalMin": sum(d["focusMin"] for d in days),
        "sessions": sum(d["sessions"] for d in days),
        "dayCount": sum(1 for d in days if d["focusMin"]),
        "days": days[:60],
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/today":
                self.respond(today_payload())
                return
            if path == "/api/config":
                self.respond(load_config())
                return
            if path == "/api/stats":
                self.respond(stats_payload())
                return
            if path in STATIC:
                self.serve(PUBLIC / path.lstrip("/"), STATIC[path])
                return
            if path in ("/", "/index.html"):
                self.serve(PUBLIC / "index.html", "text/html; charset=utf-8")
                return
            self.send_error(404)
        except ValueError as error:
            self.respond({"error": str(error)}, status=400)
        except OSError as error:
            self.respond({"error": "Cannot read the vault: " + str(error)}, status=500)
        except Exception as error:
            self.respond({"error": "Server error: " + repr(error)}, status=500)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/sessions":
                self.respond(log_session(payload))
                return
            if path == "/api/sessions/delete":
                self.respond(delete_session(payload))
                return
            if path == "/api/config":
                config = save_config(payload)
                self.respond({**today_payload(config), "ok": True})
                return
            self.send_error(404)
        except ValueError as error:
            self.respond({"error": str(error)}, status=400)
        except json.JSONDecodeError:
            self.respond({"error": "Invalid JSON"}, status=400)
        except OSError as error:
            self.respond({"error": "Cannot write to the vault: " + str(error)}, status=500)
        except Exception as error:
            self.respond({"error": "Server error: " + repr(error)}, status=500)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length < 0 or length > MAX_BODY:
            raise ValueError("Request is too large")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data

    def respond(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve(self, file_path: Path, content_type: str) -> None:
        if not file_path.is_file():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))


def lan_ip() -> str:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        return ip
    except OSError:
        return "your-pc-ip"


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"On this PC:  http://127.0.0.1:{PORT}")
    print(f"On phone:    http://{lan_ip()}:{PORT}  (same Wi-Fi)")
    server.serve_forever()


if __name__ == "__main__":
    main()
