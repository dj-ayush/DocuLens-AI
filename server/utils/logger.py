import logging
import json


class JsonFormatter(logging.Formatter):
  def format(self, record: logging.LogRecord) -> str:
    payload = {
      "timestamp": self.formatTime(record, self.datefmt),
      "level": record.levelname,
      "logger": record.name,
      "message": record.getMessage(),
    }
    if record.exc_info:
      payload["exception"] = self.formatException(record.exc_info)
    return json.dumps(payload)

def setup_logger(name="ragbot") -> logging.Logger:
  logger = logging.getLogger(name)
  logger.setLevel(logging.INFO)
  logger.propagate = False
  formatter = JsonFormatter()

  if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

  return logger

logger = setup_logger()
