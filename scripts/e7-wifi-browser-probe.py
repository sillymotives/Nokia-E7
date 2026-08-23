#!/usr/bin/env python3
"""Nokia E7 local Wi-Fi/browser capability probe, version 2.

Binds plain HTTP to one explicitly selected local IPv4 interface, serves a
small old-browser-compatible page, records bounded request/capability evidence,
then packages a redacted report. It makes no outbound network connection.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import subprocess
import tarfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit


SCRIPT_VERSION = "2"
DEFAULT_PORT = 8765
MAX_WAIT_SECONDS = 600
POST_ROOT_WAIT_SECONDS = 35
POST_REPORT_WAIT_SECONDS = 5

ID15_RE = re.compile(r"(?<![0-9])[0-9]{15}(?![0-9])")

HTML = b"""<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KAI E7 Link</title>
  <link rel="stylesheet" type="text/css" href="/probe.css">
</head>
<body>
  <div id="card">
    <div id="sigil">KAI // E7</div>
    <h1>LAN LINK ESTABLISHED</h1>
    <p>The Nokia E7 reached the host over Wi-Fi.</p>
    <p id="js">Waiting for JavaScript...</p>
    <img src="/pixel.gif" width="1" height="1" alt="">
  </div>
  <script type="text/javascript" src="/probe.js"></script>
</body>
</html>
"""

CSS = b"""html,body{margin:0;padding:0;background:#071018;color:#d7f7ff;font-family:Arial,sans-serif;}
#card{margin:24px auto;padding:20px;width:520px;max-width:82%;border:2px solid #4ad7e8;background:#102432;}
#sigil{color:#ff86cf;font-size:14px;letter-spacing:3px;}h1{font-size:24px;margin:10px 0;color:#6fffe9;}
p{font-size:16px;line-height:1.35;margin:8px 0;}#js{color:#ffd166;}
"""

JS = b"""(function(){
  var values=[];
  function add(k,v){values.push(encodeURIComponent(k)+'='+encodeURIComponent(String(v)));}
  function exists(v){return typeof v !== 'undefined';}
  var canvas=false, audio=false, video=false;
  try{canvas=!!document.createElement('canvas').getContext;}catch(e){}
  try{audio=!!document.createElement('audio').canPlayType;}catch(e){}
  try{video=!!document.createElement('video').canPlayType;}catch(e){}
  add('js',1);
  add('screen',exists(window.screen)?screen.width+'x'+screen.height:'unknown');
  add('viewport',document.documentElement.clientWidth+'x'+document.documentElement.clientHeight);
  add('dpr',window.devicePixelRatio||1);
  add('touch',('ontouchstart' in window));
  add('xhr',exists(window.XMLHttpRequest));
  add('canvas',canvas);
  add('audio',audio);
  add('video',video);
  add('websocket',exists(window.WebSocket));
  add('worker',exists(window.Worker));
  add('geolocation',!!navigator.geolocation);
  add('localstorage',exists(window.localStorage));
  add('appcache',exists(window.applicationCache));
  var status=document.getElementById('js');
  if(status){status.innerHTML='JavaScript answered. Capability report sent.';status.style.color='#6fffe9';}
  var beacon=new Image();
  beacon.src='/report?'+values.join('&')+'&stamp='+(new Date().getTime());
  if(exists(window.XMLHttpRequest)){
    try{
      var request=new XMLHttpRequest();
      request.onreadystatechange=function(){
        if(request.readyState===4){var done=new Image();done.src='/report?xhr_status='+request.status;}
      };
      request.open('GET','/xhr',true);request.send(null);
    }catch(e){var failed=new Image();failed.src='/report?xhr_exception=1';}
  }
})();
"""

GIF_1X1 = bytes.fromhex(
    "47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def redact(value: str, ipv4_values: tuple[str, ...] = ()) -> str:
    value = ID15_RE.sub("[15-digit-id-redacted]", value)
    for address in sorted(ipv4_values, key=len, reverse=True):
        value = value.replace(address, "[ipv4-redacted]")
    return value


def local_interfaces() -> list[tuple[str, str, ipaddress.IPv4Network]]:
    result = subprocess.run(
        ["ip", "-o", "-4", "addr", "show", "up", "scope", "global"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    found: list[tuple[str, str, ipaddress.IPv4Network]] = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if "inet" not in fields or len(fields) < 4:
            continue
        iface = fields[1]
        cidr = fields[fields.index("inet") + 1]
        interface = ipaddress.ip_interface(cidr)
        if isinstance(interface, ipaddress.IPv4Interface):
            found.append((str(interface.ip), iface, interface.network))
    return found


def default_source() -> str | None:
    result = subprocess.run(
        ["ip", "-4", "route", "get", "1.1.1.1"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    match = re.search(r"(?:^|\s)src\s+(\d+(?:\.\d+){3})(?:\s|$)", result.stdout)
    return match.group(1) if match else None


class ProbeState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.events: list[dict[str, object]] = []
        self.capabilities: dict[str, list[str]] = {}
        self.resources: set[str] = set()
        self.root_seen_at: float | None = None
        self.report_seen_at: float | None = None
        self.rejected_clients = 0
        self.e7_user_agent_seen = False

    def record(
        self,
        path: str,
        client_ip: str,
        headers: dict[str, str],
        allowed: bool,
    ) -> None:
        parsed = urlsplit(path)
        with self.lock:
            self.events.append(
                {
                    "utc": utc_now(),
                    "path": parsed.path,
                    "client": client_ip,
                    "allowed": allowed,
                    "headers": headers,
                }
            )
            if not allowed:
                self.rejected_clients += 1
                return
            self.resources.add(parsed.path)
            user_agent = headers.get("User-Agent", "")
            if re.search(r"(?:NokiaE7(?:-00)?|E7-00)", user_agent, re.IGNORECASE):
                self.e7_user_agent_seen = True
            if parsed.path == "/" and self.root_seen_at is None:
                self.root_seen_at = time.monotonic()
            if parsed.path == "/report":
                for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
                    if key != "stamp":
                        self.capabilities.setdefault(key, []).extend(values)
                if self.report_seen_at is None:
                    self.report_seen_at = time.monotonic()


def make_handler(state: ProbeState, allowed_network: ipaddress.IPv4Network):
    class Handler(BaseHTTPRequestHandler):
        server_version = "KAI-E7-Probe/1"
        sys_version = ""

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

        def do_GET(self) -> None:  # noqa: N802
            client_ip = self.client_address[0]
            try:
                allowed = ipaddress.ip_address(client_ip) in allowed_network
            except ValueError:
                allowed = False
            selected_headers = {
                key: self.headers.get(key, "")
                for key in (
                    "Host",
                    "User-Agent",
                    "Accept",
                    "Accept-Language",
                    "Accept-Encoding",
                    "Connection",
                )
                if self.headers.get(key) is not None
            }
            selected_headers["Host"] = redact(
                selected_headers.get("Host", ""), (str(self.server.server_address[0]),)
            )
            state.record(self.path, client_ip, selected_headers, allowed)
            if not allowed:
                self._send(403, "text/plain; charset=utf-8", b"Local subnet only.\n")
                return

            route = urlsplit(self.path).path
            if route == "/":
                self._send(200, "text/html; charset=utf-8", HTML)
            elif route == "/probe.css":
                self._send(200, "text/css; charset=utf-8", CSS)
            elif route == "/probe.js":
                self._send(200, "application/javascript; charset=utf-8", JS)
            elif route == "/pixel.gif":
                self._send(200, "image/gif", GIF_1X1)
            elif route == "/xhr":
                self._send(200, "text/plain; charset=utf-8", b"xhr-ok\n")
            elif route == "/report":
                self._send(204, "text/plain; charset=utf-8", b"")
            elif route == "/favicon.ico":
                self._send(204, "image/x-icon", b"")
            else:
                self._send(404, "text/plain; charset=utf-8", b"Not found.\n")

    return Handler


def write_report(
    report: Path,
    state: ProbeState,
    bind_ip: str,
    iface: str,
    network: ipaddress.IPv4Network,
    port: int,
    started: str,
    finish_reason: str,
) -> int:
    root_seen = state.root_seen_at is not None
    js_seen = "js" in state.capabilities
    e7_seen = state.e7_user_agent_seen
    status = 0 if root_seen and e7_seen else 4
    lines = [
        "NOKIA E7 LOCAL WI-FI/BROWSER PROBE",
        f"Script version: {SCRIPT_VERSION}",
        f"UTC start: {started}",
        f"UTC finish: {utc_now()}",
        "Policy: same-subnet plain HTTP only; no outbound requests",
        f"Bound interface: {iface} [ipv4-redacted]:{port}",
        "Allowed network: [ipv4-redacted]",
        f"Finish reason: {finish_reason}",
        f"Allowed request count: {sum(1 for event in state.events if event['allowed'])}",
        f"Rejected request count: {state.rejected_clients}",
        f"Root page reached: {int(root_seen)}",
        f"E7 user-agent identity reached: {int(e7_seen)}",
        f"JavaScript report reached: {int(js_seen)}",
        "",
        "=== Requested resources ===",
    ]
    lines.extend(sorted(state.resources) or ["(none)"])
    lines.extend(["", "=== JavaScript capability report ==="])
    if state.capabilities:
        for key in sorted(state.capabilities):
            values = ", ".join(state.capabilities[key])
            lines.append(f"{key}: {values}")
    else:
        lines.append("(none)")
    lines.extend(["", "=== Request evidence ==="])
    for index, event in enumerate(state.events, 1):
        lines.append(
            f"Request {index}: utc={event['utc']} path={event['path']} "
            f"client=[ipv4-redacted] allowed={int(bool(event['allowed']))}"
        )
        for key, value in dict(event["headers"]).items():
            lines.append(f"  {key}: {redact(value)}")
    lines.append("")
    if root_seen and e7_seen:
        lines.append("PASS: the E7 reached and rendered the host page over local Wi-Fi.")
        if js_seen:
            lines.append("PASS: browser JavaScript returned a capability report.")
        else:
            lines.append("PARTIAL: no JavaScript capability report was received.")
    elif root_seen:
        lines.append("PARTIAL: a local client reached the page, but its user agent did not identify as E7-00.")
    else:
        lines.append("PARTIAL: no browser request reached the probe.")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(report, 0o600)
    return status


def package(start_dir: Path, run_dir: Path, run_name: str) -> tuple[Path, Path]:
    bundle = start_dir / f"{run_name}.tar.gz"
    checksum = start_dir / f"{run_name}.tar.gz.sha256"
    with tarfile.open(bundle, "w:gz") as archive:
        archive.add(run_dir, arcname=run_name, recursive=True)
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {bundle.name}\n", encoding="ascii")
    os.chmod(bundle, 0o600)
    os.chmod(checksum, 0o600)
    return bundle, checksum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", help="local IPv4 address to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    start_dir = Path.cwd().resolve()
    if str(start_dir).startswith(("/media/", "/run/media/", "/mnt/")):
        print(f"REFUSED: run from host storage, not {start_dir}")
        return 2
    if not 1024 <= args.port <= 65535:
        print("REFUSED: port must be between 1024 and 65535.")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"nokia-e7-wifi-browser-{stamp}"
    run_dir = start_dir / run_name
    run_dir.mkdir(mode=0o700)
    report = run_dir / "wifi-browser.txt"
    next_file = run_dir / "NEXT.txt"
    started = utc_now()
    state = ProbeState()
    finish_reason = "preflight failure"

    try:
        interfaces = local_interfaces()
    except (OSError, subprocess.SubprocessError) as error:
        report.write_text(f"REFUSED: could not enumerate local IPv4 interfaces: {error}\n")
        next_file.write_text("No listener was started.\n")
        bundle, checksum = package(start_dir, run_dir, run_name)
        print(f"PARTIAL: interface discovery failed.\nBundle:   {bundle}\nChecksum: {checksum}")
        return 3

    available = {ip: (iface, network) for ip, iface, network in interfaces}
    bind_ip = args.bind or default_source()
    if bind_ip not in available:
        choices = ", ".join(f"{iface}={ip}" for ip, iface, _network in interfaces) or "none"
        report.write_text(
            "REFUSED: selected/default IPv4 is not an active global interface. "
            f"Choices: {redact(choices, tuple(available))}\n"
        )
        next_file.write_text("No listener was started. Rerun with --bind ADDRESS if appropriate.\n")
        bundle, checksum = package(start_dir, run_dir, run_name)
        print("PARTIAL: no suitable default interface was selected.")
        print(f"Available interfaces: {choices}")
        print(f"Bundle:   {bundle}\nChecksum: {checksum}")
        return 3

    iface, network = available[bind_ip]
    handler = make_handler(state, network)
    try:
        server = HTTPServer((bind_ip, args.port), handler, bind_and_activate=True)
    except OSError as error:
        report.write_text(f"REFUSED: listener failed: {redact(str(error), (bind_ip,))}\n")
        next_file.write_text("No listener was started.\n")
        bundle, checksum = package(start_dir, run_dir, run_name)
        print(f"PARTIAL: listener failed.\nBundle:   {bundle}\nChecksum: {checksum}")
        return 3

    server.timeout = 1
    url = f"http://{bind_ip}:{args.port}/"
    print("Nokia E7 local Wi-Fi/browser probe is listening.")
    print(f"Interface: {iface}")
    print(f"On the E7, open exactly: {url}")
    print(f"Waiting up to {MAX_WAIT_SECONDS // 60} minutes; Ctrl-C packages partial evidence.")

    deadline = time.monotonic() + MAX_WAIT_SECONDS
    try:
        while time.monotonic() < deadline:
            server.handle_request()
            now = time.monotonic()
            if state.report_seen_at is not None and now - state.report_seen_at >= POST_REPORT_WAIT_SECONDS:
                finish_reason = "JavaScript report received"
                break
            if state.root_seen_at is not None and now - state.root_seen_at >= POST_ROOT_WAIT_SECONDS:
                finish_reason = "root reached; JavaScript wait elapsed"
                break
        else:
            finish_reason = "ten-minute listener timeout"
    except KeyboardInterrupt:
        finish_reason = "operator interrupted listener"
    finally:
        server.server_close()

    status = write_report(report, state, bind_ip, iface, network, args.port, started, finish_reason)
    next_file.write_text(
        "Nokia E7 local Wi-Fi/browser probe finished.\n\n"
        f"Root page reached: {int(state.root_seen_at is not None)}\n"
        f"E7 user-agent identity reached: {int(state.e7_user_agent_seen)}\n"
        f"JavaScript report reached: {int('js' in state.capabilities)}\n\n"
        "Expected shareable files:\n"
        f"  {run_name}.tar.gz\n"
        f"  {run_name}.tar.gz.sha256\n",
        encoding="utf-8",
    )
    os.chmod(next_file, 0o600)
    bundle, checksum = package(start_dir, run_dir, run_name)
    if status == 0:
        print("PASS: Nokia E7 reached the host over local Wi-Fi.")
    else:
        print("PARTIAL: no E7-identified root-page request was captured.")
    print(f"Bundle:   {bundle}")
    print(f"Checksum: {checksum}")
    print("No outbound connection or deliberate phone-data write was made by the probe.")
    print("Ordinary browser history or session state may have changed.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
