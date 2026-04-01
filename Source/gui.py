import ctypes
import os

try:
    import tkinter as tk
    from tkinter import messagebox
    import tkinter.ttk as ttk
except ImportError:
    tk = None
    messagebox = None
    ttk = None


def _windows_message_box(title: str, message: str, flags: int) -> int:
    try:
        return ctypes.windll.user32.MessageBoxW(0, str(message), str(title), flags)
    except Exception:
        return 0


def _configure_ttk_style(root):
    if ttk is None:
        return
    try:
        style = ttk.Style(root)
        for theme in ("clam", "vista", "xpnative", "alt", "default"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("Modern.TFrame", background="#f4f5f7")
        style.configure("Modern.TLabel", background="#f4f5f7", foreground="#1f2937", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#f4f5f7", foreground="#111827", font=("Segoe UI", 11, "bold"))
        style.configure("Modern.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 6))
        style.configure("Modern.TCheckbutton", background="#f4f5f7", foreground="#1f2937", font=("Segoe UI", 10))
    except Exception:
        pass


def _center_window(root, width=None, height=None):
    root.update_idletasks()
    if width is None or height is None:
        width = root.winfo_width() or root.winfo_reqwidth()
        height = root.winfo_height() or root.winfo_reqheight()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)
    root.geometry(f"{width}x{height}+{x}+{y}")


def _show_result_dialog(title: str, message: str, is_error: bool = False) -> bool:
    if tk is None or ttk is None:
        return False
    try:
        root = tk.Tk()
        root.title(title)
        root.resizable(False, False)
        root.configure(bg="#f4f5f7")
        _configure_ttk_style(root)

        frame = ttk.Frame(root, style="Modern.TFrame", padding=20)
        frame.pack(fill="both", expand=True)

        icon_text = "⚠️" if is_error else "✅"
        header = ttk.Label(frame, text=f"{icon_text} {title}", style="Header.TLabel", anchor="w", justify="left")
        header.pack(fill="x", pady=(0, 10))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(0, 10))

        message_label = ttk.Label(frame, text=message, style="Modern.TLabel", wraplength=520, justify="left")
        message_label.pack(fill="x", pady=(0, 20))

        button = ttk.Button(frame, text="OK", command=root.destroy, style="Modern.TButton")
        button.pack(anchor="e")

        _center_window(root, 560, 200)
        root.attributes("-topmost", True)
        root.deiconify()
        root.lift()
        root.focus_force()
        root.after(100, lambda: root.attributes("-topmost", False))
        root.mainloop()
        return True
    except Exception:
        return False


def request_user_consent() -> bool:
    def console_consent() -> bool:
        print(
            "This application will collect system information and send it to tournament admins "
            "as a verification anti-alt account check.\n"
            "The app will only run during verification and then stop and be deleted.\n"
            "The information will be stored only for tournament admins to see.\n"
            "\n"
            "Please type 'yes' to agree and continue, or 'no' to cancel."
        )
        while True:
            try:
                answer = input("Agree and continue? (yes/no): ").strip().lower()
            except EOFError:
                return False
            if answer in ("yes", "y"):
                return True
            if answer in ("no", "n"):
                return False
            print("Please enter 'yes' or 'no'.")

    def native_windows_consent() -> bool:
        flags = 0x00050024  # MB_YESNO | MB_ICONQUESTION | MB_SETFOREGROUND | MB_TOPMOST
        result = _windows_message_box(
            "User Consent",
            "This application will collect system information and send it to tournament admins as a verification anti-alt account check.\n"
            "The app will only run during verification and then stop and be deleted.\n"
            "The information will be stored only for tournament admins to see.\n\n"
            "Do you agree to continue?",
            flags,
        )
        return result == 6  # IDYES

    if tk is not None and ttk is not None:
        try:
            consent = {"value": False}
            root = tk.Tk()
            root.title("User Consent")
            root.resizable(False, False)
            root.configure(bg="#f4f5f7")
            _configure_ttk_style(root)

            frame = ttk.Frame(root, style="Modern.TFrame", padding=20)
            frame.pack(fill="both", expand=True)

            header = ttk.Label(frame, text="User Consent", style="Header.TLabel", anchor="w", justify="left")
            header.pack(fill="x")
            ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(10, 15))

            label = ttk.Label(
                frame,
                text=(
                    "This application will collect system information and send it to tournament admins "
                    "as a verification anti-alt account check.\n"
                    "The app will only run during verification and then stop and be deleted.\n"
                    "The information will be stored only for tournament admins to see.\n\n"
                    "Please agree to continue."
                ),
                style="Modern.TLabel",
                wraplength=500,
                justify="left",
            )
            label.pack(fill="x", pady=(0, 20))

            agreed = tk.BooleanVar(value=False)
            check = ttk.Checkbutton(frame, text="I agree to continue", variable=agreed, style="Modern.TCheckbutton")
            check.pack(anchor="w", pady=(0, 20))

            def on_continue():
                if not agreed.get():
                    if messagebox is not None:
                        messagebox.showwarning("Agreement required", "You must agree to continue.")
                    return
                consent["value"] = True
                root.destroy()

            button = ttk.Button(frame, text="Continue", command=on_continue, style="Modern.TButton")
            button.state(["disabled"])
            button.pack(anchor="e")

            def update_button(*args):
                if agreed.get():
                    button.state(["!disabled"])
                else:
                    button.state(["disabled"])

            agreed.trace_add("write", update_button)

            _center_window(root)
            root.attributes("-topmost", True)
            root.deiconify()
            root.lift()
            root.focus_force()
            root.after(100, lambda: root.attributes("-topmost", False))

            root.mainloop()
            return consent["value"]
        except Exception:
            print("Could not show the GUI consent dialog. Falling back to native prompt.")

    if os.name == "nt":
        return native_windows_consent()

    return console_consent()
