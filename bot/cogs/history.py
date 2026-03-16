"""History cog — /history add | view"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db.crud as crud
from bot.utils.embeds import error_embed, history_embed, success_embed
from db.models import ConcertHistoryStatus
from db.session import AsyncSessionLocal
from core.logger import get_logger

logger = get_logger(__name__)


class HistoryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    history = app_commands.Group(name="history", description="管理演唱會歷史紀錄")

    @history.command(name="add", description="手動新增一筆演唱會歷史紀錄")
    @app_commands.describe(
        concert_name="演唱會名稱",
        artist="表演者",
        venue="場地",
        status="出席狀態",
        notes="備注（選填）",
    )
    @app_commands.choices(status=[
        app_commands.Choice(name="已參加", value="attended"),
        app_commands.Choice(name="未購到/錯過", value="missed"),
        app_commands.Choice(name="追蹤中", value="tracking"),
    ])
    async def history_add(
        self,
        interaction: discord.Interaction,
        concert_name: str,
        artist: str,
        venue: str,
        status: str = "attended",
        notes: str | None = None,
    ) -> None:
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

            concert = await crud.create_concert(
                db,
                name=concert_name,
                artist=artist,
                venue=venue,
                city="",
                ticket_url="",
                platform="kktix",  # default for manual entries
            )
            await crud.add_concert_history(
                db,
                user_id=user.id,
                concert_id=concert.id,
                status=ConcertHistoryStatus(status),
                notes=notes,
            )
            await db.commit()

        await interaction.followup.send(
            embed=success_embed(f"已新增歷史紀錄：**{concert_name}**")
        )

    @history.command(name="view", description="查看你的演唱會歷史紀錄")
    async def history_view(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            user = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not user:
                await interaction.followup.send(embed=error_embed("你還沒有任何歷史紀錄。"))
                return
            entries = await crud.get_concert_history(db, user.id)

        entries_data = [
            {
                "status": e.status.value,
                "notes": e.notes,
                "concert": {
                    "name": e.concert.name,
                    "venue": e.concert.venue,
                },
            }
            for e in entries
        ]
        await interaction.followup.send(embed=history_embed(entries_data))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HistoryCog(bot))
