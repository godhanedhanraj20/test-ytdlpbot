import re

with open("core/worker.py", "r") as f:
    content = f.read()

# Import FFmpegMissingError
content = content.replace("from services.downloader import download_video, CancelledError, AuthError, ExtractionError, NetworkError", "from services.downloader import download_video, CancelledError, AuthError, ExtractionError, NetworkError, FFmpegMissingError")

# Catch exception
ffmpeg_catch = """
        except FFmpegMissingError as e:
            logger.error(f"Worker failed job {job_id} permanently due to FFmpegMissingError: {e}")
            await set_job_status(job_id, user_id, "failed")
            await remove_active_job(job_id)
            return {
                "status": "error",
                "error_type": "FFmpegMissingError",
                "message": "⚠️ Audio merging not supported on server. Please install ffmpeg."
            }
"""
content = re.sub(r"        except AuthError as e:", ffmpeg_catch.strip("\n") + "\n            \n        except AuthError as e:", content)

with open("core/worker.py", "w") as f:
    f.write(content)
