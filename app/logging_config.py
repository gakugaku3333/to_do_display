import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(level: str = "INFO"):
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール出力
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # ファイル出力（ローテーション: 5MB x 3世代）
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        "logs/dashboard.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    # サードパーティのノイズを抑制
    for noisy in ("apscheduler", "googleapiclient.discovery", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
