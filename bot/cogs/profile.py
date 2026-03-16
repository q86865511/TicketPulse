"""Profile cog — /profile | /profile view @user"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db.crud as crud
from bot.utils.embeds import error_embed, profile_embed
from db.models import ProfileVisibility
from db.session import AsyncSessionLocal
from core.logger import get_logger

logger = get_logger(__name__)


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    profile_group = app_commands.Group(name="profile", description="查看個人資料")

    @profile_group.command(name="me", description="查看你自己的個人資料")
    async def profile_me(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._show_profile(interaction, str(interaction.user.id), self_view=True)

    @profile_group.command(name="view", description="查看其他用戶的個人資料")
    @app_commands.describe(member="要查看的用戶")
    async def profile_view(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._show_profile(interaction, str(member.id), self_view=False)

    async def _show_profile(
        self,
        interaction: discord.Interaction,
        target_discord_id: str,
        self_view: bool,
    ) -> None:
        async with AsyncSessionLocal() as db:
            target = await crud.get_user_by_discord_id(db, target_discord_id)
            if not target:
                await interaction.followup.send(embed=error_embed("找不到該用戶的資料。"))
                return

            # Privacy check
            if not self_view:
                viewer = await crud.get_user_by_discord_id(db, str(interaction.user.id))
                if target.profile_visibility == ProfileVisibility.PRIVATE:
                    await interaction.followup.send(embed=error_embed("此用戶的個人資料為私人設定。"))
                    return
                if target.profile_visibility == ProfileVisibility.FRIENDS:
                    if not viewer:
                        await interaction.followup.send(embed=error_embed("此用戶的個人資料僅限好友查看。"))
                        return
                    friendship = await crud.get_friendship(db, viewer.id, target.id)
                    if not friendship or friendship.status.value != "accepted":
                        await interaction.followup.send(embed=error_embed("此用戶的個人資料僅限好友查看。"))
                        return

            history = await crud.get_concert_history(db, target.id)
            watchlist = await crud.get_watchlist(db, target.id)

        attended_count = sum(1 for e in history if e.status.value == "attended")
        watching_count = sum(1 for w in watchlist if w.status.value == "watching")

        user_data = {
            "username": target.username,
            "avatar_url": target.avatar_url,
            "profile_visibility": target.profile_visibility.value,
        }
        await interaction.followup.send(embed=profile_embed(user_data, attended_count, watching_count))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
