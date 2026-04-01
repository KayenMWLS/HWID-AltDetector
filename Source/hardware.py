import glob
import os
import platform
import socket
import subprocess
import sys
import uuid


def _format_mac(mac_int: int) -> str:
    return ":".join(f"{(mac_int >> i) & 0xff:02x}" for i in range(40, -8, -8))


def get_mac_address():
    try:
        if os.name == "nt":
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-NetAdapter | Where-Object { $_.PhysicalAdapter -and $_.MacAddress } "
                    "| Select-Object -First 1).MacAddress",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            mac = result.stdout.strip()
            if mac:
                return mac
        elif sys.platform == "darwin":
            result = subprocess.run(
                ["/bin/sh", "-c", "ifconfig 2>/dev/null | awk '/ether/{print $2; exit}'"],
                capture_output=True,
                text=True,
            )
            mac = result.stdout.strip()
            if mac:
                return mac
        else:
            for path in sorted(glob.glob("/sys/class/net/*/address")):
                if path.split(os.sep)[-2] == "lo":
                    continue
                with open(path, encoding="utf-8") as f:
                    mac = f.read().strip()
                    if mac and mac != "00:00:00:00:00:00":
                        return mac
        return _format_mac(uuid.getnode())
    except Exception as e:
        return f"Could not obtain MAC address: {e}"


def get_pc_name():
    try:
        return socket.gethostname()
    except Exception as e:
        return f"Unknown ({e})"


_VM_INDICATORS = [
    ("virtualbox", "VirtualBox"),
    ("vmware", "VMware"),
    ("vbox", "VirtualBox"),
    ("kvm", "KVM"),
    ("hyper-v", "Hyper-V"),
    ("hyperv", "Hyper-V"),
    ("microsoft corporation", "Hyper-V"),
    ("xen", "Xen"),
    ("qemu", "QEMU"),
    ("bochs", "Bochs"),
    ("parallels", "Parallels"),
    ("bhyve", "bhyve"),
]


def _find_vm_label(text: str):
    if not text:
        return None
    lower_text = str(text).strip().lower()
    for marker, label in _VM_INDICATORS:
        if marker in lower_text:
            return label
    return None


def detect_vm():
    """Detect a likely virtual machine environment."""
    candidates = []

    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_ComputerSystem | Select-Object -ExpandProperty Manufacturer, Model",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            candidates.extend(result.stdout.splitlines())
        except Exception:
            pass
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_BIOS | Select-Object -ExpandProperty Manufacturer, SerialNumber",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            candidates.extend(result.stdout.splitlines())
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                check=True,
            )
            candidates.extend(result.stdout.splitlines())
        except Exception:
            pass
    else:
        dmi_paths = [
            "/sys/class/dmi/id/sys_vendor",
            "/sys/class/dmi/id/product_name",
            "/sys/class/dmi/id/product_version",
            "/sys/class/dmi/id/board_vendor",
            "/sys/class/dmi/id/bios_vendor",
            "/sys/class/dmi/id/board_name",
        ]
        for path in dmi_paths:
            try:
                with open(path, encoding="utf-8") as f:
                    candidates.append(f.read())
            except Exception:
                pass
        try:
            result = subprocess.run(
                ["hostnamectl"],
                capture_output=True,
                text=True,
                check=True,
            )
            candidates.extend(result.stdout.splitlines())
        except Exception:
            pass

    for item in candidates:
        label = _find_vm_label(item)
        if label:
            return True, label

    return False, None


def get_windows_version():
    if os.name != "nt":
        return platform.platform()
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            product = winreg.QueryValueEx(key, "ProductName")[0]
            display = ""
            try:
                display = winreg.QueryValueEx(key, "DisplayVersion")[0]
            except FileNotFoundError:
                try:
                    display = winreg.QueryValueEx(key, "ReleaseId")[0]
                except FileNotFoundError:
                    display = ""
            build = ""
            try:
                build = str(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
            except FileNotFoundError:
                try:
                    build = str(winreg.QueryValueEx(key, "CurrentBuild")[0])
                except FileNotFoundError:
                    build = ""
            ubr = ""
            try:
                ubr = str(winreg.QueryValueEx(key, "UBR")[0])
            except FileNotFoundError:
                ubr = ""

        if product:
            version_parts = [product.strip()]
        else:
            version_parts = ["Windows"]
        if display:
            version_parts.append(display.strip())
        if build:
            build_str = build.strip()
            if ubr:
                build_str = f"{build_str}.{ubr.strip()}"
            version_parts.append(build_str)
        return " ".join(part for part in version_parts if part)
    except Exception:
        pass
    return platform.platform()


def _format_bytes(value):
    try:
        value = int(value)
    except (ValueError, TypeError):
        return "Unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024.0


def get_total_ram():
    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            value = result.stdout.strip().splitlines()[0].strip()
            if value and value.isdigit():
                return _format_bytes(value)
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if line.strip().lower().startswith("totalphysicalmemory="):
                    value = line.split("=", 1)[1].strip()
                    if value.isdigit():
                        return _format_bytes(value)
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=True,
            )
            return _format_bytes(result.stdout.strip())
        except Exception:
            pass
    else:
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        value = line.split()[1]
                        return _format_bytes(int(value) * 1024)
        except Exception:
            pass
    return "Unknown"


def get_cpu_name():
    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "reg",
                    "query",
                    r"HKLM\HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                    "/v",
                    "ProcessorNameString",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if "ProcessorNameString" in line:
                    parts = line.split("    ")
                    if len(parts) >= 3:
                        value = parts[-1].strip()
                        if value:
                            return value
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if line.strip() and not line.lower().startswith("name"):
                    return line.strip()
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            pass
    else:
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    processor = platform.processor() or "Unknown"
    return processor if processor else "Unknown"


def get_gpu_name():
    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -and $_.Name.Trim() -ne '' }).Name | Select-Object -First 1",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            value = result.stdout.strip().splitlines()[0].strip()
            if value:
                return value
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "Name", "/value"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if line.strip().lower().startswith("name="):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if "Chipset Model:" in line or "Chipset model:" in line or "Graphics/Displays" in line:
                    name = line.split(":", 1)[-1].strip()
                    if name:
                        return name
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if "vga compatible controller" in line.lower() or "3d controller" in line.lower():
                    return line.split(":", 2)[-1].strip()
        except Exception:
            pass
    return "Unknown"


def get_pc_specs():
    return {
        "System": f"{platform.system() or 'Unknown'} {platform.release() or ''}".strip(),
        "CPU": get_cpu_name(),
        "GPU": get_gpu_name(),
        "RAM": get_total_ram(),
    }


def get_disk_serials():
    serials = []

    def _normalize(value):
        if value is None:
            return ""
        return str(value).strip()

    if os.name == "nt":
        checks = [
            ["powershell", "-NoProfile", "-Command", "Get-WmiObject Win32_PhysicalMedia | Select-Object -ExpandProperty SerialNumber"],
            ["powershell", "-NoProfile", "-Command", "Get-WmiObject Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"],
            ["wmic", "diskdrive", "get", "SerialNumber"],
        ]
        for cmd in checks:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                for line in result.stdout.splitlines():
                    serial = _normalize(line)
                    if serial and serial.lower() != "serialnumber":
                        serials.append(serial)
            except Exception:
                pass
        return [s for s in dict.fromkeys(serials) if s]

    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPSerialATADataType"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if "serial number" in line.lower():
                    serial = _normalize(line.split(":", 1)[-1])
                    if serial:
                        serials.append(serial)
        except Exception:
            pass
    else:
        for path in glob.glob("/sys/block/*/device/serial"):
            try:
                with open(path, encoding="utf-8") as f:
                    serial = _normalize(f.read())
                    if serial:
                        serials.append(serial)
            except Exception:
                pass
    return [s for s in dict.fromkeys(serials) if s]


def get_motherboard_serials():
    serials = []

    def _normalize(value):
        if value is None:
            return ""
        return str(value).strip()

    if os.name == "nt":
        checks = [
            ["powershell", "-NoProfile", "-Command", "Get-WmiObject Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"],
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"],
            ["wmic", "baseboard", "get", "SerialNumber"],
        ]
        for cmd in checks:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                for line in result.stdout.splitlines():
                    serial = _normalize(line)
                    if serial and serial.lower() != "serialnumber":
                        serials.append(serial)
            except Exception:
                pass
        return [s for s in dict.fromkeys(serials) if s]

    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if "serial number" in line.lower():
                    serial = _normalize(line.split(":", 1)[-1])
                    if serial:
                        serials.append(serial)
        except Exception:
            pass
    else:
        paths = [
            "/sys/class/dmi/id/board_serial",
            "/sys/devices/virtual/dmi/id/board_serial",
            "/sys/devices/platform/board_serial",
        ]
        for path in paths:
            try:
                with open(path, encoding="utf-8") as f:
                    serial = _normalize(f.read())
                    if serial:
                        serials.append(serial)
            except Exception:
                pass
        if not serials:
            try:
                result = subprocess.run(
                    ["dmidecode", "-s", "baseboard-serial-number"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                serial = _normalize(result.stdout)
                if serial:
                    serials.append(serial)
            except Exception:
                pass
    return [s for s in dict.fromkeys(serials) if s]
