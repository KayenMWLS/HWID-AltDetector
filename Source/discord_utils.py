import glob
import json
import os
import re
import socket
import struct
import subprocess
import tempfile
from datetime import datetime

_DEFAULT_RPC_CLIENT_IDS = ("1043899576722002001", "383226320970055681")


def _format_discord_user(user: dict) -> str:
    if not user:
        return ""
    display = (user.get("global_name") or user.get("display_name") or "").strip()
    un = (user.get("username") or "").strip()
    disc = str(user.get("discriminator") or "0")
    if un and disc and disc != "0":
        handle = f"{un}#{disc}"
    elif un:
        handle = un
    else:
        handle = ""

    parts = []
    if display:
        parts.append(f"display: {display}")
    if handle:
        parts.append(f"username: {handle}")
    if parts:
        return " | ".join(parts)
    return "Unknown"


def _user_from_ipc_message(msg: dict):
    if not isinstance(msg, dict):
        return None
    if msg.get("evt") == "ERROR" or msg.get("cmd") == "ERROR":
        return None
    if msg.get("evt") == "READY" and isinstance(msg.get("data"), dict):
        u = msg["data"].get("user")
        if isinstance(u, dict):
            return u
    if msg.get("cmd") == "DISPATCH" and msg.get("evt") == "READY":
        data = msg.get("data")
        if isinstance(data, dict):
            u = data.get("user")
            if isinstance(u, dict):
                return u
    data = msg.get("data")
    if isinstance(data, dict):
        u = data.get("user")
        if isinstance(u, dict):
            return u
    return None


def _ipc_read_frame(read_exact_fn):
    header = read_exact_fn(8)
    if len(header) < 8:
        return None
    _opcode, length = struct.unpack("<II", header)
    if length > 10_000_000:
        return None
    body = read_exact_fn(length) if length else b""
    if len(body) < length:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _ipc_write_frame(write_fn, opcode: int, payload: dict) -> None:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    packet = struct.pack("<II", opcode, len(data)) + data
    write_fn(packet)


def _write_all_stream(stream):
    def write_fn(packet: bytes) -> None:
        mv = memoryview(packet)
        while len(mv):
            n = stream.write(mv)
            if n is None:
                n = len(mv)
            if not n:
                raise OSError("short write")
            mv = mv[n:]

    return write_fn


def _read_exact_stream(stream):
    def read_exact(n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = stream.read(n - len(buf))
            if not chunk:
                break
            buf.extend(chunk)
        return bytes(buf)

    return read_exact


def _try_discord_ipc_user():
    env_id = (os.environ.get("DISCORD_RPC_CLIENT_ID") or "").strip()
    client_ids = (env_id,) if env_id else _DEFAULT_RPC_CLIENT_IDS

    if os.name == "nt":
        for i in range(10):
            pipe = rf"\\.\pipe\discord-ipc-{i}"
            for cid in client_ids:
                try:
                    f = open(pipe, "r+b", buffering=0)
                except OSError:
                    break
                try:
                    _ipc_write_frame(_write_all_stream(f), 0, {"v": 1, "client_id": str(cid)})
                    f.flush()
                    read_exact = _read_exact_stream(f)
                    for _ in range(20):
                        msg = _ipc_read_frame(read_exact)
                        if not msg:
                            break
                        u = _user_from_ipc_message(msg)
                        if u:
                            return u
                except OSError:
                    pass
                finally:
                    try:
                        f.close()
                    except OSError:
                        pass
        return None

    if not hasattr(socket, "AF_UNIX"):
        return None

    runtime = os.environ.get("XDG_RUNTIME_DIR") or ""
    dirs_try = [runtime, tempfile.gettempdir(), "/tmp"]
    paths = []
    for base in dirs_try:
        if not base:
            continue
        for i in range(10):
            paths.append(os.path.join(base, f"discord-ipc-{i}"))
    seen = set()
    for path in paths:
        if path in seen or not os.path.exists(path):
            continue
        seen.add(path)
        for cid in client_ids:
            sock = None
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect(path)

                def w(data: bytes):
                    sock.sendall(data)

                _ipc_write_frame(w, 0, {"v": 1, "client_id": str(cid)})

                def r(n):
                    chunks = []
                    left = n
                    while left > 0:
                        part = sock.recv(left)
                        if not part:
                            break
                        chunks.append(part)
                        left -= len(part)
                    return b"".join(chunks)

                for _ in range(20):
                    msg = _ipc_read_frame(r)
                    if not msg:
                        break
                    u = _user_from_ipc_message(msg)
                    if u:
                        return u
            except OSError:
                pass
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
    return None


def get_discord_name():
    manual = (os.environ.get("DISCORD_USERNAME") or "").strip()
    if manual:
        return manual
    try:
        user = _try_discord_ipc_user()
        if user:
            return _format_discord_user(user)
    except Exception:
        pass
    return "Unknown (open Discord app; optional: set DISCORD_USERNAME or DISCORD_RPC_CLIENT_ID)"


def detect_discord_accounts():
    account_ids = set()
    usernames = set()
    paths = []
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        for base in (appdata, localappdata):
            if not base:
                continue
            for name in ("discord", "Discord"):
                path = os.path.join(base, name, "Local Storage", "leveldb")
                if os.path.isdir(path):
                    paths.append(path)
    else:
        runtime = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        if runtime:
            path = os.path.join(runtime, "discord", "Local Storage", "leveldb")
            if os.path.isdir(path):
                paths.append(path)

    user_id_pattern = re.compile(rb'"user_id"\s*[:=]\s*"(\d{17,20})"')
    id_pattern = re.compile(rb'"id"\s*[:=]\s*"(\d{17,20})"')
    username_pattern = re.compile(rb'"username"\s*:\s*"([^\"]+)"', re.IGNORECASE)
    discriminator_pattern = re.compile(rb'"discriminator"\s*:\s*"(\d{4})"', re.IGNORECASE)
    username_pair_pattern = re.compile(
        rb'"username"\s*:\s*"([^\"]+)"[^\n\r]{0,256}?"discriminator"\s*:\s*"(\d{4})"',
        re.IGNORECASE,
    )
    for path in paths:
        for filename in glob.glob(os.path.join(path, "*")):
            if not filename.lower().endswith((".log", ".ldb", ".sst")):
                continue
            try:
                with open(filename, "rb") as f:
                    data = f.read(5_000_000)
            except Exception:
                continue
            for matcher in (user_id_pattern, id_pattern):
                for match in matcher.finditer(data):
                    try:
                        account_ids.add(match.group(1).decode("ascii", errors="ignore"))
                    except Exception:
                        pass
            for match in username_pair_pattern.finditer(data):
                try:
                    username = match.group(1).decode("utf-8", errors="ignore")
                    discriminator = match.group(2).decode("utf-8", errors="ignore")
                    if username:
                        usernames.add(f"{username}#{discriminator}")
                except Exception:
                    pass
            if not usernames:
                for match in username_pattern.finditer(data):
                    try:
                        username = match.group(1).decode("utf-8", errors="ignore")
                        if username:
                            usernames.add(username)
                    except Exception:
                        pass
    count = max(len(usernames), len(account_ids))
    has_multiple = len(usernames) > 1 or len(account_ids) > 1
    return count, has_multiple, sorted(usernames), sorted(account_ids)


def get_discord_creation_info(account_id: str):
    try:
        timestamp_ms = (int(account_id) >> 22) + 1420070400000
        created = datetime.utcfromtimestamp(timestamp_ms / 1000.0)
        age_days = max(0, (datetime.utcnow() - created).days)
        return created, age_days
    except Exception:
        return None, None
