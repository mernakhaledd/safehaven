#!/usr/bin/env python3
"""
Safe Haven Control Panel
========================
Central controller GUI for the Safe Haven AI services on Raspberry Pi.
It does NOT touch any model code - it only runs the same systemctl
commands you already use in the terminal:

    sudo systemctl start|stop|restart  face_recognition
    sudo systemctl start|stop|restart  fall_detection
    sudo systemctl start|stop|restart  help_gesture

Requires: pip3 install customtkinter
"""

import subprocess
import threading
import customtkinter as ctk

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
SERVICES = [
    {"id": "face_recognition", "name": "Face Recognition", "icon": "👤"},
    {"id": "fall_detection",   "name": "Fall Detection",   "icon": "🚨"},
    {"id": "help_gesture",     "name": "Help Gesture",     "icon": "✋"},
]

POLL_INTERVAL_MS = 1000          # how often to refresh statuses
DEFAULT_DEMO_SECONDS = 10

COLORS = {
    "active":       ("#16a34a", "🟢 RUNNING"),
    "activating":   ("#d97706", "🟡 LOADING"),
    "deactivating": ("#d97706", "🟡 STOPPING"),
    "failed":       ("#dc2626", "🔴 ERROR"),
    "inactive":     ("#475569", "⚪ STOPPED"),
}
ACCENT       = "#3b82f6"
CARD_BG      = "#1e293b"
APP_BG       = "#0f172a"
GREEN_BTN    = "#16a34a"
GREEN_HOVER  = "#15803d"
RED_BTN      = "#dc2626"
RED_HOVER    = "#b91c1c"
GRAY_BTN     = "#334155"
GRAY_HOVER   = "#475569"


# ----------------------------------------------------------------------
# systemctl helpers (run in background threads so the UI never freezes)
# ----------------------------------------------------------------------
def systemctl(action: str, service: str) -> None:
    subprocess.run(
        ["sudo", "systemctl", action, service],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def get_status(service: str) -> str:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except Exception:
        return "inactive"


def run_async(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


# ----------------------------------------------------------------------
# Service card widget
# ----------------------------------------------------------------------
class ServiceCard(ctk.CTkFrame):
    def __init__(self, master, service: dict):
        super().__init__(master, corner_radius=16, fg_color=CARD_BG)
        self.service = service

        self.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            self, text=f'{service["icon"]}  {service["name"]}',
            font=ctk.CTkFont(size=19, weight="bold"),
        ).grid(row=0, column=0, columnspan=3, pady=(18, 6), padx=16)

        self.status_label = ctk.CTkLabel(
            self, text="⚪ CHECKING…",
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=10, fg_color="#475569",
            text_color="white", width=160, height=34,
        )
        self.status_label.grid(row=1, column=0, columnspan=3, pady=(4, 14))

        btn_font = ctk.CTkFont(size=14, weight="bold")
        ctk.CTkButton(
            self, text="▶ Start", font=btn_font, width=86, height=38,
            corner_radius=10, fg_color=GREEN_BTN, hover_color=GREEN_HOVER,
            command=lambda: run_async(systemctl, "start", service["id"]),
        ).grid(row=2, column=0, padx=(16, 4), pady=(0, 18), sticky="e")
        ctk.CTkButton(
            self, text="⏹ Stop", font=btn_font, width=86, height=38,
            corner_radius=10, fg_color=RED_BTN, hover_color=RED_HOVER,
            command=lambda: run_async(systemctl, "stop", service["id"]),
        ).grid(row=2, column=1, padx=4, pady=(0, 18))
        ctk.CTkButton(
            self, text="🔄 Restart", font=btn_font, width=86, height=38,
            corner_radius=10, fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
            command=lambda: run_async(systemctl, "restart", service["id"]),
        ).grid(row=2, column=2, padx=(4, 16), pady=(0, 18), sticky="w")

    def set_status(self, status: str):
        color, text = COLORS.get(status, COLORS["inactive"])
        self.status_label.configure(fg_color=color, text=text)


# ----------------------------------------------------------------------
# Main application
# ----------------------------------------------------------------------
class SafeHavenApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("Safe Haven Control Panel")
        self.geometry("980x560")
        self.minsize(760, 520)
        self.configure(fg_color=APP_BG)

        self.demo_running = False

        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="cards")
        self.grid_rowconfigure(1, weight=1)

        # ---------- header ----------
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew",
                    padx=24, pady=(20, 8))
        ctk.CTkLabel(
            header, text="🏠 Safe Haven Control Panel",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            header, text="⏹ STOP ALL", width=120, height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10, fg_color=RED_BTN, hover_color=RED_HOVER,
            command=self.stop_all,
        ).pack(side="right")

        # ---------- service cards ----------
        self.cards = {}
        for col, svc in enumerate(SERVICES):
            card = ServiceCard(self, svc)
            card.grid(row=1, column=col, sticky="nsew",
                      padx=(24 if col == 0 else 8,
                            24 if col == len(SERVICES) - 1 else 8),
                      pady=8)
            self.cards[svc["id"]] = card

        # ---------- demo panel ----------
        demo = ctk.CTkFrame(self, corner_radius=16, fg_color=CARD_BG)
        demo.grid(row=2, column=0, columnspan=3, sticky="ew",
                  padx=24, pady=(8, 20))
        demo.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            demo, text="⚡ Presentation Demo",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=0, column=0, padx=(20, 14), pady=16)

        self.demo_now_label = ctk.CTkLabel(
            demo, text="Loops all models until stopped",
            font=ctk.CTkFont(size=14), width=230, anchor="w",
        )
        self.demo_now_label.grid(row=0, column=1, padx=6, pady=16)

        self.demo_seconds = ctk.IntVar(value=DEFAULT_DEMO_SECONDS)
        slider = ctk.CTkSlider(
            demo, from_=5, to=30, number_of_steps=25,
            variable=self.demo_seconds, width=150,
            command=lambda _: self.seconds_label.configure(
                text=f"{self.demo_seconds.get()} s"),
        )
        slider.grid(row=0, column=2, padx=(14, 4), pady=16)
        self.seconds_label = ctk.CTkLabel(
            demo, text=f"{DEFAULT_DEMO_SECONDS} s",
            font=ctk.CTkFont(size=14, weight="bold"), width=40,
        )
        self.seconds_label.grid(row=0, column=3, padx=(0, 10))

        self.demo_button = ctk.CTkButton(
            demo, text="⚡ Run Demo", width=170, height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=10, fg_color=ACCENT, hover_color="#2563eb",
            command=self.start_demo,
        )
        self.demo_button.grid(row=0, column=5, padx=(6, 20), pady=16,
                              sticky="e")

        self.poll_status()

    # ------------------------------------------------------------------
    def stop_all(self):
        for svc in SERVICES:
            run_async(systemctl, "stop", svc["id"])

    # ------------------------------------------------------------------
    # status polling (worker thread reads systemctl, UI updated via .after)
    # ------------------------------------------------------------------
    def poll_status(self):
        def worker():
            statuses = {s["id"]: get_status(s["id"]) for s in SERVICES}
            self.after(0, lambda: self.apply_statuses(statuses))
        threading.Thread(target=worker, daemon=True).start()
        self.after(POLL_INTERVAL_MS, self.poll_status)

    def apply_statuses(self, statuses: dict):
        for sid, status in statuses.items():
            self.cards[sid].set_status(status)

    # ------------------------------------------------------------------
    # demo mode: loop through ALL models, N seconds each, until stopped
    # ------------------------------------------------------------------
    SWITCH_GAP_MS = 3000   # camera needs a few seconds to be released

    def start_demo(self):
        if self.demo_running:
            self.stop_demo()
            return
        self.demo_running = True
        self.demo_index = 0
        self.demo_button.configure(text="⏹ Stop Demo",
                                   fg_color=RED_BTN, hover_color=RED_HOVER)
        # make sure nothing is holding the camera, then wait before starting
        self.stop_all()
        self.demo_now_label.configure(text="⏳ Preparing camera…")
        self.after(self.SWITCH_GAP_MS, self.run_demo_step)

    def run_demo_step(self):
        if not self.demo_running:
            return
        svc = SERVICES[self.demo_index % len(SERVICES)]
        self.current_demo = svc
        run_async(systemctl, "start", svc["id"])
        self.countdown(self.demo_seconds.get())

    def countdown(self, remaining: int):
        if not self.demo_running:
            return
        if remaining > 0:
            self.demo_now_label.configure(
                text=f'▶ {self.current_demo["icon"]} '
                     f'{self.current_demo["name"]} — {remaining} s')
            self.after(1000, lambda: self.countdown(remaining - 1))
        else:
            run_async(systemctl, "stop", self.current_demo["id"])
            self.demo_index += 1
            self.demo_now_label.configure(text="⏳ Switching model…")
            self.after(self.SWITCH_GAP_MS, self.run_demo_step)

    def stop_demo(self):
        self.demo_running = False
        if getattr(self, "current_demo", None):
            run_async(systemctl, "stop", self.current_demo["id"])
        self.demo_now_label.configure(text="Loops all models until stopped")
        self.demo_button.configure(text="⚡ Run Demo",
                                   fg_color=ACCENT, hover_color="#2563eb")


if __name__ == "__main__":
    SafeHavenApp().mainloop()
