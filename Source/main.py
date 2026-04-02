import os
import sys

from hardware import get_mac_address, get_pc_name, get_disk_serials, get_motherboard_serials, get_pc_specs, detect_vm
from discord_utils import get_discord_name, detect_discord_accounts
from network import get_country, get_public_ip, detect_vpn
from history import detect_duplicate_scan
from risk import compute_alt_risk_score
from notifier import send_to_discord
from gui import _show_result_dialog, request_user_consent, _windows_message_box

WEBHOOK_URL = (
    ""
    ""
)


def main():
    if not request_user_consent():
        sys.exit(0)

    pc_name = get_pc_name()
    mac = get_mac_address()
    discord_name = get_discord_name()
    country = get_country()
    disk_serials_list = get_disk_serials()
    disk_serials = ", ".join(disk_serials_list) if disk_serials_list else "Unknown"
    motherboard_serials_list = get_motherboard_serials()
    motherboard_serials = ", ".join(motherboard_serials_list) if motherboard_serials_list else "Unknown"
    vpn_detected, vpn_name = detect_vpn()
    public_ip = get_public_ip()
    vm_detected, vm_name = detect_vm()
    (
        discord_account_count,
        other_discord_accounts,
        discord_usernames,
        discord_account_ids,
    ) = detect_discord_accounts()
    duplicate, duplicate_accounts = detect_duplicate_scan(
        pc_name,
        mac,
        disk_serials_list,
        motherboard_serials_list,
        discord_usernames,
        discord_account_ids,
    )
    risk_score = compute_alt_risk_score(duplicate, vpn_detected, discord_account_count, vm_detected)
    pc_specs = get_pc_specs()

    failure_reasons = []
    if vpn_detected:
        failure_reasons.append(
            f"VPN active, please stop your vpn and try again{f' ({vpn_name})' if vpn_name else ''}"
        )
    if vm_detected:
        failure_reasons.append(
            f"Virtual machine detected{f' ({vm_name})' if vm_name else ''}"
        )
    if duplicate:
        failure_reasons.append("Hardware/device already scanned")
    if other_discord_accounts:
        failure_reasons.append("Alternate Discord account detected")

    verification_status = "Failed" if failure_reasons else "Passed"

    send_to_discord(
        pc_name,
        mac,
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
        WEBHOOK_URL,
    )

    if failure_reasons:
        final_title = "Verification Failed"
        final_message = "Verification failed: " + "; ".join(failure_reasons)
        if duplicate:
            if duplicate_accounts:
                final_message += (
                    "\nDetected previously by Discord account(s): "
                    + ", ".join(duplicate_accounts)
                )
            else:
                final_message += "\nDetected previously by another scan."
    else:
        final_title = "Verification Complete"
        final_message = "Verification is done. You may now continue with your activities."

    dialog_shown = _show_result_dialog(final_title, final_message, bool(failure_reasons))

    if not dialog_shown:
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            if failure_reasons:
                messagebox.showerror(final_title, final_message)
            else:
                messagebox.showinfo(final_title, final_message)
            root.destroy()
            dialog_shown = True
        except Exception:
            pass

    if not dialog_shown and os.name == "nt":
        try:
            _windows_message_box(
                final_title,
                final_message,
                0x00050040,  # MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST
            )
        except Exception:
            pass

    print(final_message)


if __name__ == "__main__":
    main()
