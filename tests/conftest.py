import os


os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("REFRESH_SECRET_KEY", "y" * 32)
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
os.environ.setdefault("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1,[::1]")
os.environ.setdefault("MAX_REQUEST_SIZE", "1048576")
os.environ.setdefault("MAX_UPLOAD_SIZE", "1048576")
os.environ.setdefault("MAX_RESPONSE_SIZE", "1048576")
os.environ.setdefault("REQUEST_TIMEOUT_SECONDS", "5")
os.environ.setdefault("MAX_REDIRECTS", "5")
