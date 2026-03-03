import os
import sqlite3
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID_ENV = os.getenv("GUILD_ID", "")
ADMIN_ROLE_NAME = os.getenv("ADMIN_ROLE_NAME", "Admin")
DB_PATH = os.getenv("VOUCH_DB_PATH", "vouches.db")

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN in .env")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                vouch_channel_id INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vouches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                voucher_user_id INTEGER NOT NULL,
                voucher_name TEXT NOT NULL,
                target_user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by_user_id INTEGER,
                review_note TEXT
            )
            """
        )


def member_is_admin(interaction: discord.Interaction) -> bool:
    if not interaction.user:
        return False
    if isinstance(interaction.user, discord.Member):
        if interaction.user.guild_permissions.administrator:
            return True
        return any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles)
    return False


def get_vouch_channel_id(guild_id: int) -> Optional[int]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT vouch_channel_id FROM guild_settings WHERE guild_id = ?", (guild_id,)
        ).fetchone()
        return row["vouch_channel_id"] if row else None


def set_vouch_channel_id(guild_id: int, channel_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO guild_settings (guild_id, vouch_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id)
            DO UPDATE SET vouch_channel_id = excluded.vouch_channel_id
            """,
            (guild_id, channel_id),
        )


def add_vouch(guild_id: int, voucher: discord.User | discord.Member, target: discord.User | discord.Member, reason: str) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO vouches (
                guild_id, voucher_user_id, voucher_name, target_user_id,
                reason, created_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                guild_id,
                voucher.id,
                str(voucher),
                target.id,
                reason,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        return int(cursor.lastrowid)


def update_vouch_status(vouch_id: int, status: str, reviewer_id: int, note: Optional[str]) -> bool:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE vouches
            SET status = ?, reviewed_by_user_id = ?, review_note = ?
            WHERE id = ?
            """,
            (status, reviewer_id, note, vouch_id),
        )
        return cursor.rowcount > 0


def vouches_for_target(guild_id: int, target_user_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(
            conn.execute(
                """
                SELECT * FROM vouches
                WHERE guild_id = ? AND target_user_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (guild_id, target_user_id, limit),
            ).fetchall()
        )


def pending_vouches(guild_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(
            conn.execute(
                """
                SELECT * FROM vouches
                WHERE guild_id = ? AND status = 'pending'
                ORDER BY id DESC LIMIT ?
                """,
                (guild_id, limit),
            ).fetchall()
        )


def top_vouched_members(guild_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(
            conn.execute(
                """
                SELECT target_user_id, COUNT(*) as total
                FROM vouches
                WHERE guild_id = ? AND status = 'approved'
                GROUP BY target_user_id
                ORDER BY total DESC, target_user_id ASC
                LIMIT ?
                """,
                (guild_id, limit),
            ).fetchall()
        )


@bot.event
async def on_ready() -> None:
    init_db()
    if GUILD_ID_ENV:
        guild_obj = discord.Object(id=int(GUILD_ID_ENV))
        tree.copy_global_to(guild=guild_obj)
        await tree.sync(guild=guild_obj)
    else:
        await tree.sync()
    print(f"Logged in as {bot.user} ({bot.user.id})")


@tree.command(name="setvouchchannel", description="Set the channel where vouch notifications are posted.")
@app_commands.describe(channel="The channel used for vouch notifications")
async def set_vouch_channel(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    if not member_is_admin(interaction):
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    set_vouch_channel_id(interaction.guild.id, channel.id)
    await interaction.response.send_message(f"✅ Vouch channel set to {channel.mention}", ephemeral=True)


@tree.command(name="vouch", description="Leave a vouch for a member (or the owner).")
@app_commands.describe(member="Who are you vouching for?", reason="Why are you vouching for them?")
async def vouch(interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
    if not interaction.guild or not interaction.user:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    reason = reason.strip()
    if len(reason) < 8:
        await interaction.response.send_message("Reason too short. Please provide at least 8 characters.", ephemeral=True)
        return

    vouch_id = add_vouch(interaction.guild.id, interaction.user, member, reason)

    await interaction.response.send_message(
        f"✅ Vouch submitted with ID **#{vouch_id}** for {member.mention}. Waiting for review.",
        ephemeral=True,
    )

    channel_id = get_vouch_channel_id(interaction.guild.id)
    if channel_id:
        channel = interaction.guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            await channel.send(
                f"🧊 New vouch **#{vouch_id}**\n"
                f"**From:** {interaction.user.mention}\n"
                f"**For:** {member.mention}\n"
                f"**Reason:** {reason}"
            )


@tree.command(name="pendingvouches", description="List recent pending vouches for moderation.")
async def pending_vouch_list(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    if not member_is_admin(interaction):
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    rows = pending_vouches(interaction.guild.id, limit=10)
    if not rows:
        await interaction.response.send_message("No pending vouches right now.", ephemeral=True)
        return

    lines = [
        f"`#{row['id']}` from <@{row['voucher_user_id']}> for <@{row['target_user_id']}> — {row['reason']}"
        for row in rows
    ]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@tree.command(name="approvevouch", description="Approve a pending vouch by ID.")
@app_commands.describe(vouch_id="The vouch ID", note="Optional mod note")
async def approve_vouch(interaction: discord.Interaction, vouch_id: int, note: Optional[str] = None) -> None:
    if not interaction.guild or not interaction.user:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    if not member_is_admin(interaction):
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    ok = update_vouch_status(vouch_id, "approved", interaction.user.id, note)
    if not ok:
        await interaction.response.send_message(f"Could not find vouch #{vouch_id}.", ephemeral=True)
        return
    await interaction.response.send_message(f"✅ Approved vouch #{vouch_id}.", ephemeral=True)


@tree.command(name="rejectvouch", description="Reject a pending vouch by ID.")
@app_commands.describe(vouch_id="The vouch ID", note="Why was it rejected?")
async def reject_vouch(interaction: discord.Interaction, vouch_id: int, note: str) -> None:
    if not interaction.guild or not interaction.user:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    if not member_is_admin(interaction):
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    ok = update_vouch_status(vouch_id, "rejected", interaction.user.id, note)
    if not ok:
        await interaction.response.send_message(f"Could not find vouch #{vouch_id}.", ephemeral=True)
        return
    await interaction.response.send_message(f"❌ Rejected vouch #{vouch_id}.", ephemeral=True)


@tree.command(name="myvouches", description="Show my recent approved vouches.")
async def my_vouches(interaction: discord.Interaction) -> None:
    if not interaction.guild or not interaction.user:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    rows = [r for r in vouches_for_target(interaction.guild.id, interaction.user.id, limit=10) if r["status"] == "approved"]
    if not rows:
        await interaction.response.send_message("You have no approved vouches yet.", ephemeral=True)
        return

    lines = [f"`#{r['id']}` from **{r['voucher_name']}** — {r['reason']}" for r in rows]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@tree.command(name="vouchboard", description="Show top members by approved vouch count.")
async def vouch_board(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    rows = top_vouched_members(interaction.guild.id, limit=10)
    if not rows:
        await interaction.response.send_message("No approved vouches yet.", ephemeral=True)
        return

    lines = [f"**{idx}.** <@{row['target_user_id']}> — `{row['total']}` vouches" for idx, row in enumerate(rows, start=1)]
    await interaction.response.send_message("🏆 **Vouch Leaderboard**\n" + "\n".join(lines))


@tree.command(name="helpvouch", description="List all vouch bot commands.")
async def help_vouch(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        "\n".join(
            [
                "`/vouch <member> <reason>` — submit a vouch",
                "`/myvouches` — see your approved vouches",
                "`/vouchboard` — top approved vouches",
                "`/setvouchchannel <channel>` — set announce channel (admin)",
                "`/pendingvouches` — list pending entries (admin)",
                "`/approvevouch <id> [note]` — approve (admin)",
                "`/rejectvouch <id> <note>` — reject (admin)",
            ]
        ),
        ephemeral=True,
    )


bot.run(TOKEN)
