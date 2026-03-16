"""Settings cog — /settings notifications | privacy"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db.crud as crud
from bot.utils.embeds import error_embed, success_embed
from db.models import NotificationPreference, ProfileVisibility
from db.session import AsyncSessionLocal
from core.logger import get_logger

logger = get_logger(__name__)


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    settings = app_commands.Group(name="settings", description="管理個人設定")

    @settings.command(name="notifications", description="設定提醒方式")
    @app_commands.describe(method="提醒方式")
    @app_commands.choices(method=[
        app_commands.Choice(name="Discord 私訊 (DM)", value="discord_dm"),
        app_commands.Choice(name="Discord 頻道提及", value="discord_channel"),
        app_commands.Choice(name="Email", value="email"),
        app_commands.Choice(name="Discord DM + Email", value="both"),
    ])
    async def notifications(self, interaction: discord.Interaction, method: str) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            user = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not user:
                user = await crud.create_user(
                    db,
                    discord_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    avatar_url=str(interaction.user.display_avatar.url),
                )

            if method in ("email", "both") and not user.email:
                await interaction.followup.send(
                    embed=error_embed(
                        "你尚未設定 Email 地址。請先透過 Web App 登入並綁定 Email，才能使用 Email 提醒功能。"
                    )
                )
                return

            await crud.update_user_preferences(
                db, user.id, notification_preference=NotificationPreference(method)
            )
            await db.commit()

        method_names = {
            "discord_dm": "Discord 私訊",
            "discord_channel": "Discord 頻道提及",
            "email": "Email",
            "both": "Discord DM + Email",
        }
        await interaction.followup.send(
            embed=success_embed(f"提醒方式已更新為：**{method_names.get(method, method)}**")
        )

    @settings.command(name="privacy", description="設定個人資料可見度")
    @app_commands.describe(visibility="可見度設定")
    @app_commands.choices(visibility=[
        app_commands.Choice(name="公開", value="public"),
        app_commands.Choice(name="僅好友", value="friends"),
        app_commands.Choice(name="私人", value="private"),
    ])
    async def privacy(self, interaction: discord.Interaction, visibility: str) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            user = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not user:
                user = await crud.create_user(
                    db,
                    discord_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    avatar_url=str(interaction.user.display_avatar.url),
                )
            await crud.update_user_preferences(
                db, user.id, profile_visibility=ProfileVisibility(visibility)
            )
            await db.commit()

        vis_map = {"public": "🌐 公開", "friends": "👥 僅好友", "private": "🔒 私人"}
        await interaction.followup.send(
            embed=success_embed(f"個人資料可見度已設定為：**{vis_map.get(visibility, visibility)}**")
        )

    @settings.command(name="quiethours", description="設定勿擾時段（不發送提醒）")
    @app_commands.describe(start="開始小時 (0-23)", end="結束小時 (0-23)")
    async def quiet_hours(
        self, interaction: discord.Interaction, start: int, end: int
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not (0 <= start <= 23 and 0 <= end <= 23):
            await interaction.followup.send(embed=error_embed("小時數必須在 0–23 之間。"))
            return

        async with AsyncSessionLocal() as db:
            user = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not user:
                user = await crud.create_user(
                    db,
                    discord_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                )
            await crud.update_user_preferences(
                db, user.id, quiet_hours_start=start, quiet_hours_end=end
            )
            await db.commit()

        await interaction.followup.send(
            embed=success_embed(f"勿擾時段已設定為 **{start:02d}:00 – {end:02d}:00**")
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))
