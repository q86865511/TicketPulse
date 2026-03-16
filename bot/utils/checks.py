"""Permission and role checks for Discord commands."""
from __future__ import annotations

import discord
from discord.ext import commands


def is_guild_only():
    """Restrict command to guild (server) usage only."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(
                "此指令只能在伺服器中使用。", ephemeral=True
            )
            return False
        return True
    return discord.app_commands.check(predicate)


def is_admin():
    """Restrict command to server administrators."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:  # type: ignore[union-attr]
            await interaction.response.send_message(
                "此指令需要管理員權限。", ephemeral=True
            )
            return False
        return True
    return discord.app_commands.check(predicate)
