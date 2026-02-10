from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+psycopg://booking_user:booking_pass@postgres:5432/booking"

    jwt_secret_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    reminder_lookahead_minutes: int = 120
    booking_expire_after_start_minutes: int = 0
    celery_expiration_interval_minutes: int = 5
    celery_reminder_interval_minutes: int = 10
    auth_rate_limit_window_seconds: int = 60
    auth_register_max_attempts: int = 10
    auth_login_max_attempts: int = 20
    rate_limit_backend: str = "redis"
    rate_limit_redis_url: str = "redis://redis:6379/2"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
