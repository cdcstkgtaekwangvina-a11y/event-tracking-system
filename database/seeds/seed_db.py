import asyncio
from datetime import timezone, timedelta
from sqlmodel import SQLModel, select
from database.models.users import Users
from database.models.events import Events
from sqlmodel.ext.asyncio.session import AsyncSession
from database.models.app_db import engine
import logging
from uuid import UUID
from datetime import datetime
from database.models.settings import Settings
from src.modules.setting.setting_constants import AppConfigKey

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Vietnam timezone (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


async def seed():
    # Force table creation / recreate for all tables
    async with engine.begin() as conn:
        logger.info("Dropping existing tables to refresh schema...")
        await conn.run_sync(SQLModel.metadata.drop_all)
        logger.info("Recreating tables...")
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        try:
            exiting_user = (await session.exec(select(Users))).first()
            if exiting_user is None:
                users = [
                    Users(
                        id=UUID("11111111-1111-1111-1111-111111111111"),
                        name="Cdcstkgtaekwangvina",
                        username="admin",
                        email="Cdcstkgtaekwangvina@gmail.com",
                        role="SUPPER_ADMIN",
                        is_active=True,
                        avatar_url=None,
                        updated_at=datetime.fromisoformat(
                            "2026-06-08T22:03:57.737385+07:00"
                        ),
                        created_at=datetime.fromisoformat(
                            "2026-06-08T22:03:57.339527+07:00"
                        ),
                        password="$argon2id$v=19$m=65536,t=3,p=4$E7Z4nO5ksgZSnSbno4EWog$7e92WJ8vLO0KOhBbw0mrs0Pza0eu0NdnOn//msgkNM8",  # Admin123@
                        otp_code=None,
                        token_version=0,
                        expired_at=None,
                        google_sub=None,
                    )
                ]

                session.add_all(users)

            exiting_settings = (await session.exec(select(Settings))).first()
            if exiting_settings is None:
                settings = [
                    Settings(
                        id=AppConfigKey.file_config,
                        value={"max_size_file": 53687091200},
                    ),
                ]

                session.add_all(settings)
            await session.commit()
            logger.info("Database seeding completed successfully!")
        except Exception as e:
            print(f"Database seeding failed: {e}")
            await session.rollback()
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(seed())
