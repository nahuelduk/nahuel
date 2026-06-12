"""
Trading Bot GUI - all in one window, no browser needed
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import json
import time
import sys
from pathlib import Path

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot")
        self.root.geometry("700x600")
        self.bot_proc = None

        # Header
        header = tk.Frame(root, bg="#2c3e50", height=60)
        header.pack(fill=tk.X)
        tk.Label(header, text="🤖 Trading Bot AI", font=("Arial", 20, "bold"),
                bg="#2c3e50", fg="white").pack(pady=10)

        # Main content
        main = ttk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Status frame
        status_frame = ttk.LabelFrame(main, text="Status", padding=10)
        status_frame.pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(status_frame, text="⏸ Stopped", font=("Arial", 14, "bold"), fg="red")
        self.status_label.pack(anchor=tk.W)

        # Buttons frame
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(btn_frame, text="▶ START BOT", bg="#27ae60", fg="white",
                                  font=("Arial", 11, "bold"), width=20, command=self.start_bot)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(btn_frame, text="⏹ STOP", bg="#e74c3c", fg="white",
                                 font=("Arial", 11, "bold"), width=20, command=self.stop_bot, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Logs frame
        log_frame = ttk.LabelFrame(main, text="Bot Logs", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state=tk.DISABLED,
                                                  font=("Courier", 9), bg="#1e1e1e", fg="#00ff00")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Footer
        footer = tk.Frame(root, bg="#34495e", height=40)
        footer.pack(fill=tk.X)
        tk.Label(footer, text="Paper Trading • Binance Testnet • No Browser Needed",
                font=("Arial", 9), bg="#34495e", fg="white").pack(pady=8)

        self.start_update_logs()

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def start_bot(self):
        self.log("🚀 Starting bot...")
        self.status_label.config(text="🟢 Running", fg="green")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        def run():
            try:
                self.bot_proc = subprocess.Popen(
                    [sys.executable, "core/bot.py"],
                    cwd=Path(__file__).parent,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                for line in iter(self.bot_proc.stdout.readline, ''):
                    if line:
                        self.log(line.rstrip())
            except Exception as e:
                self.log(f"❌ Error: {e}")
                self.status_label.config(text="❌ Error", fg="red")

        threading.Thread(target=run, daemon=True).start()

    def stop_bot(self):
        if self.bot_proc:
            self.bot_proc.terminate()
            self.bot_proc.wait()
        self.log("⏹ Bot stopped")
        self.status_label.config(text="⏸ Stopped", fg="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def start_update_logs(self):
        """Check bot_state.json for portfolio updates"""
        def update():
            state_file = Path(__file__).parent / "bot_state.json"
            last_update = 0
            while True:
                try:
                    if state_file.exists():
                        stat = state_file.stat()
                        if stat.st_mtime > last_update:
                            with open(state_file) as f:
                                state = json.load(f)
                            portfolio = state.get("portfolio", {})
                            # Actualizar sin loguear todo, solo cambios
                            last_update = stat.st_mtime
                except:
                    pass
                time.sleep(1)

        threading.Thread(target=update, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()
