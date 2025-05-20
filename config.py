import os
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

    # SQLite with absolute path
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(BASE_DIR / 'instance' / 'youth_governance.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
