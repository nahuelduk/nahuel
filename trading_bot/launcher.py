"""
All-in-one launcher — starts bot and dashboard from one window
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import webbrowser
import time
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class TradingBotLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Trading Bot Launcher")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        self.bot_process = None
        self.dashboard_process = None
        self.bot_running = False
        self.dashboard_running = False

        self._build_ui()

    def _build_ui(self):
        # Title
        title = ttk.Label(self.root, text="AI Trading Bot",
                         font=("Arial", 16, "bold"))
        title.pack(pady=10)

        # Status frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.bot_status = ttk.Label(status_frame, text="🔴 Bot: Stopped",
                                    foreground="red")
        self.bot_status.pack(anchor=tk.W)

        self.dashboard_status = ttk.Label(status_frame, text="🔴 Dashboard: Stopped",
                                         foreground="red")
        self.dashboard_status.pack(anchor=tk.W)

        # Buttons frame
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.start_bot_btn = ttk.Button(btn_frame, text="▶ Start Bot",
                                        command=self._start_bot)
        self.start_bot_btn.grid(row=0, column=0, padx=5)

        self.stop_bot_btn = ttk.Button(btn_frame, text="⏹ Stop Bot",
                                       command=self._stop_bot, state=tk.DISABLED)
        self.stop_bot_btn.grid(row=0, column=1, padx=5)

        self.dashboard_btn = ttk.Button(btn_frame, text="📊 Open Dashboard",
                                       command=self._open_dashboard, state=tk.DISABLED)
        self.dashboard_btn.grid(row=0, column=2, padx=5)

        # Logs
        log_frame = ttk.LabelFrame(self.root, text="Bot Logs", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15,
                                                   state=tk.DISABLED,
                                                   font=("Courier", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Footer
        footer = ttk.Label(self.root,
                          text="API: Binance Testnet | Mode: Paper Trading",
                          font=("Arial", 9), foreground="gray")
        footer.pack(pady=5)

    def _log(self, msg):
        """Add message to log panel"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def _start_bot(self):
        if self.bot_running:
            self._log("⚠ Bot is already running")
            return

        self._log("🚀 Starting bot...")
        self.start_bot_btn.config(state=tk.DISABLED)

        try:
            self.bot_process = subprocess.Popen(
                [sys.executable, "core/bot.py"],
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.bot_running = True
            self.bot_status.config(text="🟢 Bot: Running", foreground="green")
            self.stop_bot_btn.config(state=tk.NORMAL)
            self.dashboard_btn.config(state=tk.NORMAL)
            self._log("✓ Bot started successfully")

            # Monitor bot output
            threading.Thread(target=self._monitor_bot, daemon=True).start()

        except Exception as e:
            self._log(f"✗ Error starting bot: {e}")
            self.start_bot_btn.config(state=tk.NORMAL)

    def _stop_bot(self):
        if not self.bot_running:
            return

        self._log("Stopping bot...")
        try:
            if self.bot_process:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
            self.bot_running = False
            self.bot_status.config(text="🔴 Bot: Stopped", foreground="red")
            self.start_bot_btn.config(state=tk.NORMAL)
            self.stop_bot_btn.config(state=tk.DISABLED)
            self._log("✓ Bot stopped")
        except Exception as e:
            self._log(f"✗ Error stopping bot: {e}")

    def _open_dashboard(self):
        if not self.bot_running:
            self._log("⚠ Start the bot first")
            return

        self._log("🌐 Opening dashboard...")
        time.sleep(1)  # wait for bot to be ready

        try:
            # Check if streamlit is available
            subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "dashboard.py",
                 "--logger.level=error"],
                cwd=Path(__file__).parent,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)
            webbrowser.open("http://localhost:8501")
            self.dashboard_status.config(text="🟢 Dashboard: Running",
                                        foreground="green")
            self._log("✓ Dashboard opened in browser")
        except Exception as e:
            self._log(f"✗ Error opening dashboard: {e}")

    def _monitor_bot(self):
        """Monitor bot process output"""
        if not self.bot_process:
            return
        try:
            for line in iter(self.bot_process.stdout.readline, ''):
                if line:
                    self._log(line.rstrip())
        except:
            pass

    def on_closing(self):
        self._stop_bot()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
