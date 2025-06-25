from flask import Flask
from threading import Thread
from bot import run_bot
from plot_options import start_scheduler

app = Flask('')

@app.route('/')
def index():
    return "App working!"

def run_flask():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    flask_thread = Thread(target=run_flask, daemon=True)
    scheduler_thread = Thread(target=start_scheduler, daemon=True)
    flask_thread.start()
    scheduler_thread.start()

if __name__ == "__main__":
    keep_alive()
    run_bot()  # Run Discord bot in the main thread