import subprocess
import sys
import time

def main():
    print("Starting Bot and ARQ Worker in parallel...")

    # Start the ARQ worker process using the current python executable's module loader
    worker_process = subprocess.Popen(
        [sys.executable, "-m", "arq", "core.worker.WorkerSettings"]
    )

    # Start the Pyrogram bot process
    bot_process = subprocess.Popen(
        [sys.executable, "-m", "bot.main"]
    )

    try:
        # Keep the script alive while both are running
        worker_process.wait()
        bot_process.wait()
    except KeyboardInterrupt:
        print("\n[Ctrl+C detected] Shutting down services gracefully...")

        # Send termination signals
        bot_process.terminate()
        worker_process.terminate()

        try:
            bot_process.wait(timeout=5)
            worker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_process.kill()
            worker_process.kill()

        print("Shutdown complete.")
        sys.exit(0)

if __name__ == "__main__":
    main()
