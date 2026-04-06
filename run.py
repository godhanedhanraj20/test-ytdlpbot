import subprocess
import sys
import time

def main():
    print("Starting bot...")

    # Start the Pyrogram bot process
    bot_process = subprocess.Popen(
        [sys.executable, "-m", "bot.main"]
    )

    print("Starting worker...")

    # Start the ARQ worker process using the current python executable's module loader
    worker_process = subprocess.Popen(
        [sys.executable, "-m", "arq", "core.worker.WorkerSettings"]
    )

    print("Both services running")

    try:
        # Keep the script alive while both are running
        while True:
            # Check if either process has exited
            bot_retcode = bot_process.poll()
            worker_retcode = worker_process.poll()

            if bot_retcode is not None:
                print(f"\n[ERROR] Bot process exited unexpectedly with code {bot_retcode}.")
                print("Terminating worker process...")
                worker_process.terminate()
                break

            if worker_retcode is not None:
                print(f"\n[ERROR] Worker process exited unexpectedly with code {worker_retcode}.")
                print("Terminating bot process...")
                bot_process.terminate()
                break

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[Ctrl+C detected] Shutting down services gracefully...")
    finally:
        # Send termination signals
        try:
            bot_process.terminate()
            worker_process.terminate()
        except Exception:
            pass

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
