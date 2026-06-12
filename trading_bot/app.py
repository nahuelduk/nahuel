"""
Simple GUI launcher for Trading Bot
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import sys
from pathlib import Path

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        self.bot_proc = None
        self.dash_proc = None

        # Title
        tk.Label(root, text="🤖 Trading Bot", font=("Arial", 18, "bold")).pack(pady=20)

        # Status
        self.status_label = tk.Label(root, text="Status: Ready", font=("Arial", 12))
        self.status_label.pack(pady=10)

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=20)

        self.start_btn = tk.Button(btn_frame, text="▶ Start Bot", width=15, command=self.start_bot)
        self.start_btn.pack(pady=5)

        self.dashboard_btn = tk.Button(btn_frame, text="📊 Dashboard", width=15, command=self.open_dashboard, state=tk.DISABLED)
        self.dashboard_btn.pack(pady=5)

        self.stop_btn = tk.Button(btn_frame, text="⏹ Stop", width=15, command=self.stop_bot, state=tk.DISABLED)
        self.stop_btn.pack(pady=5)

        # Info
        tk.Label(root, text="Paper Trading • Binance Testnet", font=("Arial", 9), fg="gray").pack(pady=10)

    def start_bot(self):
        self.status_label.config(text="Status: Starting bot...", fg="orange")
        self.start_btn.config(state=tk.DISABLED)
        self.dashboard_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)

        def run_bot():
            try:
                self.bot_proc = subprocess.Popen(
                    [sys.executable, "core/bot.py"],
                    cwd=Path(__file__).parent,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.status_label.config(text="Status: Bot running ✓", fg="green")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start bot: {e}")
                self.status_label.config(text="Status: Error", fg="red")
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)

        threading.Thread(target=run_bot, daemon=True).start()

    def open_dashboard(self):
        try:
            subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "dashboard.py", "--logger.level=error"],
                cwd=Path(__file__).parent,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            messagebox.showinfo("Dashboard", "Opening in browser... http://localhost:8501")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open dashboard: {e}")

    def stop_bot(self):
        if self.bot_proc:
            self.bot_proc.terminate()
            self.bot_proc.wait()
        self.status_label.config(text="Status: Stopped", fg="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.dashboard_btn.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
