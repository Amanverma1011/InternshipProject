import os
import sys
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.environ.get('DB_USER', 'sologix_app')}:"
        f"{os.environ.get('DB_PASSWORD', '')}@"
        f"{os.environ.get('DB_HOST', '127.0.0.1')}:"
        f"{os.environ.get('DB_PORT', '3306')}/"
        f"{os.environ.get('DB_NAME', 'sologix_proposals')}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    STORAGE_PATH = os.environ.get('STORAGE_PATH', 'storage/proposals')
    PDF_TIMEOUT = int(os.environ.get('PDF_TIMEOUT', '30000'))
    MAX_PROPOSALS_PER_DAY = 10

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour token validity

    # Session/cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False

    @classmethod
    def validate(cls):
        key = os.environ.get('SECRET_KEY', '')
        if not key or key == 'dev-secret-key-change-in-production':
            sys.exit('FATAL: SECRET_KEY env var not set or is default. Set a strong random key.')
        if not os.environ.get('DB_PASSWORD'):
            sys.exit('FATAL: DB_PASSWORD env var not set.')

    # Set SESSION_COOKIE_SECURE=true in .env only after HTTPS is configured
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    REMEMBER_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'


config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    cfg = config_map.get(env, DevelopmentConfig)
    if env == 'production' and hasattr(cfg, 'validate'):
        cfg.validate()
    return cfg
