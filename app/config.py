"""
配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # MySQL 配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "stockeagle"

    # 飞书推送
    FEISHU_WEBHOOK_URL: Optional[str] = None

    # 数据更新
    DATA_UPDATE_INTERVAL: int = 5  # 秒

    # 日志
    LOG_LEVEL: str = "INFO"

    # 版本
    APP_VERSION: str = "1.0.0"

    # 数据库 URL（自动构建）
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
