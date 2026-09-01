import os
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
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
