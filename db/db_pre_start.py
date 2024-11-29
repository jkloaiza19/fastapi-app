import asyncio
from database import get_database_initializer


async def init_db():
    await get_database_initializer().initialize_database()


if __name__ == "__main__":
    asyncio.run(init_db())
