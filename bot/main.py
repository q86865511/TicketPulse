"""Discord Bot entry point."""
from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from core.config import settings
from core.logger import get_logger, setup_logging
from core.notifier import Notifier
from scraper.scheduler import create_scheduler

setup_logging()
logger = get_logger(__name__)

COGS = [
    "bot.cogs.alerts",
    "bot.cogs.watchlist",
    "bot.cogs.history",
    "bot.cogs.profile",
    "bot.cogs.friends",
    "bot.cogs.settings",
]


class TicketPulseBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = False  # Not needed for slash-command-only bot
        super().__init__(command_prefix="!", intents=intents)
        self.notifier: Notifier | None = None
        self._scheduler = None

    async def setup_hook(self) -> None:
        # Load all cogs
        for cog in COGS:
            await self.load_extension(cog)
            logger.info("cog_loaded", cog=cog)

        # Sync slash commands globally
        await self.tree.sync()
        logger.info("slash_commands_synced")

        # Set up notifier and scheduler
        self.notifier = Notifier(bot=self)
        self._scheduler = create_scheduler(self.notifier)
        self._scheduler.start()
        logger.info("scheduler_started")

    async def on_ready(self) -> None:
        assert self.user is not None
        logger.info("bot_ready", user=str(self.user), id=self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="ticket drops 🎫",
            )
        )

    async def close(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        await super().close()


async def main() -> None:
    bot = TicketPulseBot()
    async with bot:
        await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
