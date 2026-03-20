import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    MT5_HOST = os.environ.get('MT5_HOST', 'localhost')
    MT5_PORT = int(os.environ.get('MT5_PORT', 8080))
    DEFAULT_MAGIC = 888999
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')