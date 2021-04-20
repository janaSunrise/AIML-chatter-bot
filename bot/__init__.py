import os
import sys
import typing as t
from datetime import datetime

import aiml
import aiohttp
import discord
from discord.ext.commands import AutoShardedBot
from loguru import logger

from bot import config

# -- Logger configuration --
logger.configure(
    handlers=[
        dict(sink=sys.stdout, format=config.log_format, level=config.log_level),
        dict(
            sink=config.log_file,
            format=config.log_format,
            level=config.log_level,
            rotation=config.log_file_size,
        ),
    ]
)


class Bot(AutoShardedBot):
    def __init__(self, channel_name: str, *args, **kwargs) -> None:
        """Initialize the subclass."""
        super().__init__(*args, **kwargs)

        # -- Prefix --
        self.default_prefix = config.COMMAND_PREFIX
        self.channel_name = channel_name

        # -- Bot info --
        self.cluster = kwargs.get("cluster_id")
        self.cluster_count = kwargs.get("cluster_count")
        self.version = kwargs.get("version")

        # -- Start time config --
        self.start_time = datetime.utcnow()
        self.last_reset_time = datetime.now()

        # -- AIML conf --
        self.aiml_kernel = aiml.Kernel()
        self.setup_aiml()

        logger.info("AIML KERNEL STARTED!")

        # -- Sessions config --
        self.session = None

        # -- Startup config --
        self.initial_call = True

    async def is_owner(self, user: discord.User) -> bool:
        if user.id in config.devs:
            return True

        return await super().is_owner(user)

    def setup_aiml(self):
        initial_dir = os.getcwd()
        os.chdir("./bot")

        self.aiml_kernel.setBotPredicate("name", "Mr Chatter")
        self.aiml_kernel.bootstrap(learnFiles=["std-startup.xml"], commands=["LOAD AIML B"])

        os.chdir(initial_dir)

    async def load_extensions(self) -> None:
        """Load all listed cogs."""
        from bot.core import loader

        for extension in loader.COGS:
            try:
                self.load_extension(extension)
                logger.info(f"Cog {extension} loaded.")
            except Exception as exc:
                logger.error(
                    f"Cog {extension} failed to load with {type(exc)}: {exc!r}"
                )
                raise exc  # Raise to get proper info about the exception.

    async def on_ready(self) -> None:
        """Functions called when the bot is ready and connected."""
        if self.initial_call:
            self.initial_call = False
            await self.load_extensions()

            logger.info("Bot is ready")
        else:
            logger.info("Bot connection reinitialized")

    def run(self, token: t.Optional[str]) -> None:
        """Run the bot and add missing token check."""
        if not token:
            logger.critical("Missing Bot Token!")
        else:
            super().run(token)

    async def start(self, *args, **kwargs) -> None:
        """Starts the bot."""
        self.session = aiohttp.ClientSession()

        await super().start(*args, **kwargs)

    async def close(self) -> None:
        """Close the bot and do some cleanup."""
        logger.info("Closing bot connection")

        if hasattr(self, "session"):
            await self.session.close()

        await super().close()
