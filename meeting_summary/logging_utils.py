from __future__ import annotations

import logging
import warnings


_NOISY_LOGGERS = (
    "matplotlib",
    "speechbrain",
    "lightning",
    "lightning_fabric",
    "pytorch_lightning",
)


class _SuppressLowSignalThirdPartyLogs(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for logger_name in _NOISY_LOGGERS:
            if record.name.startswith(logger_name) and record.levelno < logging.WARNING:
                return False
        return True


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    suppression_filter = _SuppressLowSignalThirdPartyLogs()
    for handler in logging.getLogger().handlers:
        handler.addFilter(suppression_filter)

    warnings.filterwarnings(
        "ignore",
        message=r"You are using `torch.load` with `weights_only=False`.*",
        category=Warning,
    )
