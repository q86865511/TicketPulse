"""Friends cog — /friend add | list"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db.crud as crud
from bot.utils.embeds import error_embed, success_embed
from db.session import AsyncSessionLocal
from core.logger import get_logger

logger = get_logger(__name__)


class FriendsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    friend = app_commands.Group(name="friend", description="管理好友")

    @friend.command(name="add", description="傳送好友邀請")
    @app_commands.describe(member="要加為好友的用戶")
    async def friend_add(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)

        if member.id == interaction.user.id:
            await interaction.followup.send(embed=error_embed("不能對自己送出好友邀請。"))
            return

        async with AsyncSessionLocal() as db:
            requester = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not requester:
                requester = await crud.create_user(
                    db,
                    discord_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                )

            receiver = await crud.get_user_by_discord_id(db, str(member.id))
            if not receiver:
                receiver = await crud.create_user(
                    db,
                    discord_id=str(member.id),
                    username=member.display_name,
                )

            friendship = await crud.send_friend_request(db, requester.id, receiver.id)
            await db.commit()

        if not friendship:
            await interaction.followup.send(embed=error_embed("好友邀請已存在或你們已經是好友了。"))
            return

        await interaction.followup.send(
            embed=success_embed(f"已向 **{member.display_name}** 送出好友邀請！")
        )

    @friend.command(name="list", description="查看你的好友清單")
    async def friend_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            user = await crud.get_user_by_discord_id(db, str(interaction.user.id))
            if not user:
                await interaction.followup.send(embed=error_embed("你還沒有任何好友。"))
                return
            friends = await crud.get_friends(db, user.id)

        if not friends:
            await interaction.followup.send(embed=error_embed("你目前沒有任何好友。"))
            return

        embed = discord.Embed(title="👥 好友清單", color=discord.Color.blurple())
        for f in friends[:20]:
            embed.add_field(name=f.username, value=f"Discord ID: `{f.discord_id}`", inline=False)
        embed.set_footer(text=f"共 {len(friends)} 位好友")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FriendsCog(bot))
