import json
import urllib.request
from discord_utils import get_discord_creation_info


def send_to_discord(
    pc_name,
    mac_address,
    discord_name,
    country,
    public_ip,
    duplicate,
    disk_serials,
    motherboard_serials,
    vpn_detected,
    vpn_name,
    vm_detected,
    vm_name,
    pc_specs,
    risk_score,
    discord_account_count,
    other_discord_accounts,
    discord_usernames,
    discord_account_ids,
    verification_status,
    failure_reasons,
    webhook_url,
):
    status_text = verification_status
    failure_text = ", ".join(failure_reasons) if failure_reasons else "None"
    summary = (
        f"PC name: {pc_name}\n"
        f"MAC address: {mac_address}\n"
        f"Disk serial(s): {disk_serials}\n"
        f"Motherboard serial(s): {motherboard_serials}\n"
        f"Discord: {discord_name}\n"
        f"Country: {country}\n"
        f"Public IP: {public_ip}\n"
        f"Duplicate scan: {'Yes' if duplicate else 'No'}\n"
        f"Verification status: {status_text}\n"
        f"Failure reasons: {failure_text}\n"
        f"Virtual machine detected: {'Yes' if vm_detected else 'No'}"
        + (f" ({vm_name})" if vm_detected and vm_name else "")
    )
    specs = (
        f"System: {pc_specs.get('System', 'Unknown')}\n"
        f"CPU: {pc_specs.get('CPU', 'Unknown')}\n"
        f"GPU: {pc_specs.get('GPU', 'Unknown')}\n"
        f"RAM: {pc_specs.get('RAM', 'Unknown')}"
    )
    account_list = ", ".join(discord_usernames) if discord_usernames else "Unknown"
    if len(account_list) > 500:
        account_list = account_list[:497] + "..."
    account_creation = "Unknown"
    if discord_account_ids:
        created, age_days = get_discord_creation_info(discord_account_ids[0])
        if created is not None:
            account_creation = f"{created.strftime('%Y-%m-%d')} ({age_days} days ago)"
            if len(discord_account_ids) > 1:
                account_creation += " (first account shown)"
    discord_info = (
        f"Discord accounts found: {discord_account_count}\n"
        f"Other Discord accounts: {'Yes' if other_discord_accounts else 'No'}\n"
        f"Usernames: {account_list}\n"
        f"Account created: {account_creation}\n"
        f"Alt account risk score: {risk_score}/100"
    )
    vpn_info = (
        f"VPN detected: {'Yes' if vpn_detected else 'No'}"
        + (f" ({vpn_name})" if vpn_detected and vpn_name else "")
    )
    vm_info = (
        f"Virtual machine detected: {'Yes' if vm_detected else 'No'}"
        + (f" ({vm_name})" if vm_detected and vm_name else "")
    )
    embeds = [
        {"title": "Summary", "description": summary, "color": 15105570},
        {"title": "PC specs", "description": specs, "color": 3066993},
        {"title": "VPN detection", "description": vpn_info, "color": 16711680},
        {"title": "Virtual machine detection", "description": vm_info, "color": 16776960},
        {"title": "Discord info", "description": discord_info, "color": 15158332},
    ]
    payload = {
        "content": "User information scanned.",
        "embeds": embeds,
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; MacAddressNotifier/1.0)",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()
