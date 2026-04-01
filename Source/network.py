import json
import os
import socket
import subprocess
import tempfile
import urllib.request


def _geo_http_json(url: str, timeout: float = 10.0):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_country():
    try:
        data = _geo_http_json("https://ipwho.is/")
        if isinstance(data, dict) and data.get("success") and data.get("country"):
            return str(data["country"]).strip()
    except Exception:
        pass

    try:
        data = _geo_http_json("https://ipapi.co/json/")
        if isinstance(data, dict) and not data.get("error"):
            name = (data.get("country_name") or data.get("country") or "").strip()
            if name:
                return name
    except Exception:
        pass

    try:
        data = _geo_http_json("http://ip-api.com/json/?fields=status,country,message")
        if isinstance(data, dict) and data.get("status") == "success" and data.get("country"):
            return str(data["country"]).strip()
    except Exception:
        pass

    try:
        data = _geo_http_json("https://get.geojs.io/v1/ip/country.json")
        if isinstance(data, dict) and data.get("name"):
            return str(data["name"]).strip()
    except Exception:
        pass

    try:
        data = _geo_http_json("https://ipinfo.io/json")
        if isinstance(data, dict) and data.get("country"):
            return str(data["country"]).strip()
    except Exception:
        pass
    return "Unknown"


def _http_text(url: str, timeout: float = 10.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/plain, application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8").strip()


def get_public_ip() -> str:
    try:
        data = _geo_http_json("https://api.ipify.org?format=json")
        if isinstance(data, dict) and data.get("ip"):
            return str(data["ip"]).strip()
    except Exception:
        pass

    for url in ("https://ifconfig.me/ip", "https://ipinfo.io/ip", "https://icanhazip.com"):
        try:
            ip = _http_text(url)
            if ip:
                return ip
        except Exception:
            pass

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        pass
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    return "Unknown"


def detect_vpn():
    keywords = [
        ("nordvpn", "NordVPN"),
        ("expressvpn", "ExpressVPN"),
        ("surfshark", "Surfshark"),
        ("proton vpn", "Proton VPN"),
        ("cyberghost", "CyberGhost"),
        ("private internet access", "Private Internet Access"),
        ("pia", "Private Internet Access"),
        ("ipvanish", "IPVanish"),
        ("hotspot shield", "Hotspot Shield"),
        ("proton vpn", "Proton VPN"),
        ("windscribe", "Windscribe"),
        ("tunnelbear", "TunnelBear"),
        ("hide.me", "Hide.me"),
        ("hide me", "Hide.me"),
        ("vyprvpn", "VyprVPN"),
        ("mullvad", "Mullvad"),
        ("openvpn", "OpenVPN"),
        ("wireguard", "WireGuard"),
        ("warp", "Cloudflare WARP"),
        ("cloudflare", "Cloudflare WARP"),
        ("pptp", "PPTP"),
        ("l2tp", "L2TP"),
        ("sstp", "SSTP"),
        ("cisco", "Cisco VPN"),
        ("wan miniport", "Windows WAN Miniport"),
        ("tap", "TAP adapter"),
        ("tun", "TUN adapter"),
        ("pppoe", "PPPoE"),
        ("vpn", "VPN"),
    ]
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                check=True,
            )
            text = result.stdout.lower()
        else:
            text = ""
            try:
                result = subprocess.run(
                    ["ip", "a"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                text = result.stdout.lower()
            except Exception:
                pass
            if not text:
                try:
                    result = subprocess.run(
                        ["ifconfig", "-a"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    text = result.stdout.lower()
                except Exception:
                    pass
        for keyword, label in keywords:
            if keyword in text:
                return True, label
    except Exception:
        pass
    return False, None
