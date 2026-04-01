import json
import os
import tempfile


def _get_scan_history_path():
    home = os.path.expanduser("~")
    if home and os.path.isdir(home):
        return os.path.join(home, ".mac_pc_scan_history.json")
    return os.path.join(tempfile.gettempdir(), "mac_pc_scan_history.json")


def _load_scan_history():
    path = _get_scan_history_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pc_names = set(
            str(v).strip().lower() for v in data.get("pc_names", []) if v is not None
        )
        mac_addresses = set(
            str(v).strip().lower() for v in data.get("mac_addresses", []) if v is not None
        )
        disk_serials = set(
            str(v).strip().lower() for v in data.get("disk_serials", []) if v is not None
        )
        motherboard_serials = set(
            str(v).strip().lower() for v in data.get("motherboard_serials", []) if v is not None
        )
        discord_accounts = {
            str(k).strip().lower(): {
                str(item).strip()
                for item in (v or [])
                if item is not None and str(item).strip()
            }
            for k, v in data.get("discord_accounts", {}).items()
            if k is not None
        }
        return {
            "path": path,
            "pc_names": pc_names,
            "mac_addresses": mac_addresses,
            "disk_serials": disk_serials,
            "motherboard_serials": motherboard_serials,
            "discord_accounts": discord_accounts,
        }
    except Exception:
        return {
            "path": path,
            "pc_names": set(),
            "mac_addresses": set(),
            "disk_serials": set(),
            "motherboard_serials": set(),
            "discord_accounts": {},
        }


def _save_scan_history(history):
    try:
        with open(history["path"], "w", encoding="utf-8") as f:
            json.dump(
                {
                    "pc_names": sorted(history["pc_names"]),
                    "mac_addresses": sorted(history["mac_addresses"]),
                    "disk_serials": sorted(history["disk_serials"]),
                    "motherboard_serials": sorted(history["motherboard_serials"]),
                    "discord_accounts": {
                        key: sorted(values)
                        for key, values in history.get("discord_accounts", {}).items()
                    },
                },
                f,
                indent=2,
            )
    except OSError:
        pass


def detect_duplicate_scan(
    pc_name: str,
    mac_address: str,
    disk_serials,
    motherboard_serials,
    discord_usernames=None,
    discord_account_ids=None,
):
    current_pc = str(pc_name).strip().lower()
    current_mac = str(mac_address).strip().lower()
    current_serials = {
        str(v).strip().lower()
        for v in (disk_serials or [])
        if v is not None and str(v).strip()
    }
    current_mobos = {
        str(v).strip().lower()
        for v in (motherboard_serials or [])
        if v is not None and str(v).strip()
    }
    history = _load_scan_history()
    duplicate = (
        current_pc in history["pc_names"]
        or current_mac in history["mac_addresses"]
        or any(s in history["disk_serials"] for s in current_serials)
        or any(s in history["motherboard_serials"] for s in current_mobos)
    )
    current_accounts = [
        str(v).strip()
        for v in (discord_usernames or [])
        if v is not None and str(v).strip()
    ]
    if not current_accounts:
        current_accounts = [
            str(v).strip()
            for v in (discord_account_ids or [])
            if v is not None and str(v).strip()
        ]
    matched_accounts = set()
    for identifier in [current_pc, current_mac, *current_serials, *current_mobos]:
        if identifier in history.get("discord_accounts", {}):
            matched_accounts.update(history["discord_accounts"][identifier])
    changed = False
    if current_accounts:
        history.setdefault("discord_accounts", {})
        for identifier in [current_pc, current_mac, *current_serials, *current_mobos]:
            if not identifier:
                continue
            existing = history["discord_accounts"].setdefault(identifier, set())
            for account in current_accounts:
                if account not in existing:
                    existing.add(account)
                    changed = True
    if current_pc and current_pc not in history["pc_names"]:
        history["pc_names"].add(current_pc)
        changed = True
    if current_mac and current_mac not in history["mac_addresses"]:
        history["mac_addresses"].add(current_mac)
        changed = True
    for serial in current_serials:
        if serial not in history["disk_serials"]:
            history["disk_serials"].add(serial)
            changed = True
    for serial in current_mobos:
        if serial not in history["motherboard_serials"]:
            history["motherboard_serials"].add(serial)
            changed = True
    if changed:
        _save_scan_history(history)
    return duplicate, sorted(matched_accounts)
