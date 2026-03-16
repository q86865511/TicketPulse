"""Watchlist cog — /watch add | list | remove"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db.crud as crud
from bot.utils.embeds import error_embed, success_embed, watchlist_embed
from db.session import AsyncSessionLocal
from scraper.kktix import KKTIXScraper
from scraper.tixcraft import TixCraftScraper
from scraper.ticket_plus import TicketPlusScraper
from scraper.ibon import IbonScraper
from scraper.kham import KhamScraper
from db.models import TicketPlatform
from core.logger import get_logger

logger = get_logger(__name__)


def _detect_platform(url: str) -> TicketPlatform | None:
    if "kktix.com" in url:
        return TicketPlatform.KKTIX
    if "tixcraft.com" in url:
        return TicketPlatform.TIXCRAFT
    if "ticket.com.tw" in url:
        return TicketPlatform.TICKET_PLUS
    if "ibon.7-eleven.com.tw" in url:
        return TicketPlatform.IBON
    if "kham.com.tw" in url:
        return TicketPlatform.KHAM
    return None


_SCRAPER_MAP = {
    TicketPlatform.KKTIX: KKTIXScraper(),
    TicketPlatform.TIXCRAFT: TixCraftScraper(),
    TicketPlatform.TICKET_PLUS: TicketPlusScraper(),
    TicketPlatform.IBON: IbonScraper(),
    TicketPlatform.KHAM: KhamScraper(),
}


class WatchlistCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    watch = app_commands.Group(name="watch", description="管理演唱會關注清單")

    @watch.command(name="add", description="加入一個演唱會到關注清單")
    @app_commands.describe(url="演唱會售票頁面網址")
    async def watch_add(self, interaction: discord.Interaction, url: str) -> None:
        await interaction.response.defer(ephemeral=True)

        platform = _detect_platform(url)
        if not platform:
            await interaction.followup.send(embed=error_embed("無法識別票券平台，請確認網址是否來自支援的售票網站。"))
            return

        scraper = _SCRAPER_MAP[platform]
        info = await scraper.fetch(url)
        if not info:
            await interaction.followup.send(embed=error_embed("無法取得演唱會資訊，請確認網址是否正確。"))
            return

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
                name=info.name,
                artist=info.artist,
                venue=info.venue,
                city="",
                ticket_url=url,
                platform=platform,
                date=info.date,
                seat_types=info.seat_types,
                min_price=info.price_range.get("min"),
                max_price=info.price_range.get("max"),
            )

            existing = await crud.get_watchlist_item(db, user.id, concert.id)
            if existing:
                await interaction.followup.send(embed=error_embed("此演唱會已在你的關注清單中。"))
                return

            await crud.add_to_watchlist(db, user.id, concert.id)
            await db.commit()

        await interaction.followup.send(
            embed=success_embed(f"已加入關注清單：**{info.name}**\n場地：{info.venue}")
        )

    @watch.command(name="list", description="查看你的關注清單")
    async def watch_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            user = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not user:
                await interaction.followup.send(embed=error_embed("你還沒有任何關注清單。"))
                return
            items = await crud.get_watchlist(db, user.id)

        items_data = [
            {
                "id": item.id,
                "status": item.status.value,
                "concert": {
                    "name": item.concert.name,
                    "venue": item.concert.venue,
                },
            }
            for item in items
        ]
        await interaction.followup.send(embed=watchlist_embed(items_data))

    @watch.command(name="remove", description="從關注清單移除演唱會")
    @app_commands.describe(item_id="關注清單中的 ID（使用 /watch list 查詢）")
    async def watch_remove(self, interaction: discord.Interaction, item_id: int) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            user = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not user:
                await interaction.followup.send(embed=error_embed("找不到你的帳號。"))
                return
            removed = await crud.remove_from_watchlist(db, user.id, item_id)
            await db.commit()

        if removed:
            await interaction.followup.send(embed=success_embed(f"已從關注清單移除 ID `{item_id}`。"))
        else:
            await interaction.followup.send(embed=error_embed("找不到該項目，請確認 ID 是否正確。"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WatchlistCog(bot))
