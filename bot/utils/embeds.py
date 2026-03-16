"""Reusable Discord embed templates."""
from __future__ import annotations

from datetime import datetime

import discord


def ticket_alert_embed(
    concert_name: str,
    venue: str,
    ticket_url: str,
    price_str: str = "",
    date: datetime | None = None,
    seat_types: list[str] | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎫 {concert_name}",
        description="票券現已開放購票！",
        color=discord.Color.green(),
        url=ticket_url,
    )
    embed.add_field(name="場地", value=venue or "未知", inline=True)
    if date:
        embed.add_field(name="演出日期", value=discord.utils.format_dt(date, "D"), inline=True)
    if price_str:
        embed.add_field(name="票價", value=price_str, inline=True)
    if seat_types:
        embed.add_field(name="票種", value="\n".join(seat_types[:5]), inline=False)
    embed.add_field(name="購票連結", value=f"[點此購票]({ticket_url})", inline=False)
    embed.set_footer(text="TicketPulse • Feel every drop before it's gone")
    return embed


def watchlist_embed(items: list[dict]) -> discord.Embed:
    embed = discord.Embed(title="🎯 你的關注清單", color=discord.Color.blurple())
    if not items:
        embed.description = "目前沒有任何關注的演唱會。\n使用 `/watch add <網址或名稱>` 加入！"
        return embed
    for i, item in enumerate(items[:10], 1):
        concert = item.get("concert", {})
        status_emoji = {"watching": "👀", "notified": "🔔", "expired": "💤"}.get(
            item.get("status", "watching"), "👀"
        )
        embed.add_field(
            name=f"{i}. {status_emoji} {concert.get('name', '未知演唱會')}",
            value=f"ID: `{item.get('id')}` | 場地: {concert.get('venue', '-')}",
            inline=False,
        )
    embed.set_footer(text=f"共 {len(items)} 筆")
    return embed


def history_embed(entries: list[dict]) -> discord.Embed:
    embed = discord.Embed(title="📚 演唱會歷史紀錄", color=discord.Color.gold())
    if not entries:
        embed.description = "還沒有任何紀錄！使用 `/history add` 新增。"
        return embed
    for entry in entries[:10]:
        concert = entry.get("concert", {})
        status_emoji = {"attended": "✅", "missed": "❌", "tracking": "👀"}.get(
            entry.get("status", "tracking"), "📌"
        )
        embed.add_field(
            name=f"{status_emoji} {concert.get('name', '未知')}",
            value=f"場地: {concert.get('venue', '-')} | 備注: {entry.get('notes') or '無'}",
            inline=False,
        )
    embed.set_footer(text=f"共 {len(entries)} 筆")
    return embed


def profile_embed(user: dict, history_count: int, watching_count: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"👤 {user.get('username', 'Unknown')} 的個人資料",
        color=discord.Color.teal(),
    )
    if user.get("avatar_url"):
        embed.set_thumbnail(url=user["avatar_url"])
    embed.add_field(name="📚 已參加演唱會", value=str(history_count), inline=True)
    embed.add_field(name="🎯 正在關注", value=str(watching_count), inline=True)
    visibility = user.get("profile_visibility", "public")
    vis_map = {"public": "🌐 公開", "friends": "👥 好友", "private": "🔒 私人"}
    embed.add_field(name="隱私設定", value=vis_map.get(visibility, visibility), inline=True)
    return embed


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(title="❌ 錯誤", description=message, color=discord.Color.red())


def success_embed(message: str) -> discord.Embed:
    return discord.Embed(title="✅ 成功", description=message, color=discord.Color.green())
