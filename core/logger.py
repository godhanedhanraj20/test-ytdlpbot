import logging
import sys
import os

os.makedirs("logs", exist_ok=True)

class ServiceFormatter(logging.Formatter):
    """Custom formatter to inject the [SERVICE] tag"""
    def format(self, record):
        service = getattr(record, 'service', 'SYSTEM')
        self._style._fmt = f"[%(asctime)s] [%(levelname)s] [{service}] %(message)s"
        return super().format(record)

def setup_logger(name: str, service_name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid adding handlers multiple times if instantiated multiple times
    if not logger.handlers:
        formatter = ServiceFormatter()

        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File Handler
        fh = logging.FileHandler("logs/app.log")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # LoggerAdapter to pass the service name automatically
    return logging.LoggerAdapter(logger, {'service': service_name})
