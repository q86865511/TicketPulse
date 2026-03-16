"""Alerts cog — admin commands for managing alert channels."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.checks import is_admin
from bot.utils.embeds import error_embed, success_embed
from core.logger import get_logger

logger = get_logger(__name__)


class AlertsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Maps guild_id -> channel_id for alert broadcasts
        self._alert_channels: dict[int, int] = {}

    alerts = app_commands.Group(name="alerts", description="管理票券提醒頻道（管理員）")

    @alerts.command(name="setchannel", description="設定票券提醒的推送頻道")
    @app_commands.describe(channel="要推送提醒的文字頻道")
    @is_admin()
    async def set_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        assert interaction.guild is not None
        self._alert_channels[interaction.guild.id] = channel.id
        logger.info("alert_channel_set", guild_id=interaction.guild.id, channel_id=channel.id)
        await interaction.response.send_message(
            embed=success_embed(f"已設定票券提醒頻道為 {channel.mention}"),
            ephemeral=True,
        )

    @alerts.command(name="clearchannel", description="清除票券提醒頻道設定")
    @is_admin()
    async def clear_channel(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        self._alert_channels.pop(interaction.guild.id, None)
        await interaction.response.send_message(
            embed=success_embed("已清除票券提醒頻道設定。"),
            ephemeral=True,
        )

    def get_alert_channel_id(self, guild_id: int) -> int | None:
        return self._alert_channels.get(guild_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AlertsCog(bot))
