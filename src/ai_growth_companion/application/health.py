"""Separated liveness, readiness, and provider dependency health checks."""

import sqlite3
import sys
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ai_growth_companion.config import Settings, load_settings
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.providers.deepseek_evaluation import DEEPSEEK_MODEL
from ai_growth_companion.repositories.database import Database, migration_status


class HealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: HealthState
    detail: str


class HealthReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    liveness: ComponentHealth
    readiness: ComponentHealth
    provider_dependency: ComponentHealth
    database_version: int | None
    available_database_version: int | None

    @property
    def is_ready(self) -> bool:
        return self.readiness.state is HealthState.HEALTHY


def check_health(settings: Settings, database: Database) -> HealthReport:
    """Check local readiness without calling an external model or logging secrets."""
    liveness = ComponentHealth(state=HealthState.HEALTHY, detail="应用进程正在运行")
    current_version: int | None = None
    available_version: int | None = None

    try:
        current_version, available_version = migration_status(database)
        if current_version != available_version:
            readiness = ComponentHealth(
                state=HealthState.UNHEALTHY,
                detail=(f"数据库需要迁移：当前 {current_version}，可用 {available_version}"),
            )
        else:
            with database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "UPDATE users SET updated_at = updated_at WHERE id = ?",
                    (LOCAL_USER_ID,),
                )
                connection.rollback()
            readiness = ComponentHealth(
                state=HealthState.HEALTHY,
                detail="配置、数据库版本和写入能力均正常",
            )
    except (OSError, RuntimeError, ValueError, sqlite3.DatabaseError) as error:
        readiness = ComponentHealth(
            state=HealthState.UNHEALTHY,
            detail=f"数据库就绪检查失败：{error}",
        )

    if settings.is_fake_mode:
        dependency = ComponentHealth(
            state=HealthState.HEALTHY,
            detail="Fake Provider 本地可用，不访问外部网络",
        )
    elif (
        settings.llm_provider.casefold() == "deepseek"
        and settings.llm_model == DEEPSEEK_MODEL
        and settings.llm_api_key is not None
        and settings.llm_paid_calls_allowed
    ):
        dependency = ComponentHealth(
            state=HealthState.HEALTHY,
            detail="DeepSeek Provider 配置完整；应用不会自动重试或主动发起调用",
        )
    else:
        dependency = ComponentHealth(
            state=HealthState.DEGRADED,
            detail="真实 Provider 需要固定 DeepSeek 模型、API Key 和显式付费许可",
        )

    return HealthReport(
        liveness=liveness,
        readiness=readiness,
        provider_dependency=dependency,
        database_version=current_version,
        available_database_version=available_version,
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    settings = load_settings()
    report = check_health(settings, Database(settings.database_url))
    print(report.model_dump_json(indent=2))
    if not report.is_ready:
        sys.exit(1)


if __name__ == "__main__":
    main()
