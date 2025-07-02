import uvicorn
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler (only show INFO and above)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File handler (show DEBUG and above)
file_handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Set log level for specific loggers
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 