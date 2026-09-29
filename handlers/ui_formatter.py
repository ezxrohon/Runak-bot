# ============================================================
# 🫧🦋 ʀuɴAk - Rich UI Formatter (Premium Styling)
# ============================================================
# Centralized formatting module for rich, colorful Telegram UI
# with beautiful emojis, gradients, and interactive elements

from typing import List, Dict, Any
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---- Color & Style Gradients ----
GRADIENTS = {
    "gold": ["🟨", "🟨", "⭐"],
    "rainbow": ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪"],
    "purple": ["🟣", "🟪", "💜"],
    "blue": ["🔵", "🔷", "💙"],
    "red": ["🔴", "🔻", "❤️"],
    "cyan": ["🔷", "💎", "🟦"],
}

# ---- Premium Separators ----
SEPS = {
    "premium": "━" * 30,
    "dotted": "┈" * 30,
    "double": "═" * 30,
    "wave": "〰️ " * 15,
    "stars": "✦ " * 15,
}

# ---- Badge Icons ----
BADGES = {
    "crown": "👑",
    "diamond": "💎",
    "star": "⭐",
    "fire": "🔥",
    "bolt": "⚡",
    "skull": "💀",
    "shield": "🛡️",
    "trophy": "🏆",
    "medal": "🎖️",
    "gem": "💎",
}

class RichFormatter:
    """Premium UI formatter for beautiful Telegram messages."""
    
    @staticmethod
    def header(title: str, emoji: str = "🫧", gradient: str = "gold") -> str:
        """Create a premium header with title."""
        sep = SEPS["premium"]
        grad = " ".join(GRADIENTS.get(gradient, GRADIENTS["gold"])[:3])
        return f"\n{grad}\n{sep}\n{emoji} <b>{title}</b> {emoji}\n{sep}\n"
    
    @staticmethod
    def footer(text: str = "ʀuɴAk") -> str:
        """Create a footer."""
        return f"\n{SEPS['premium']}\n✨ <i>{text}</i> ✨\n"
    
    @staticmethod
    def section(title: str, emoji: str = "📌") -> str:
        """Create a section header."""
        return f"\n{emoji} <b>{title}</b>\n{SEPS['dotted']}"
    
    @staticmethod
    def stat_line(label: str, value: Any, emoji: str = "📊") -> str:
        """Format a stat line with label and value."""
        return f"{emoji} <b>{label}:</b> <code>{value}</code>"
    
    @staticmethod
    def badge(text: str, badge_type: str = "star") -> str:
        """Add a badge to text."""
        badge = BADGES.get(badge_type, "⭐")
        return f"{badge} {text} {badge}"
    
    @staticmethod
    def success(message: str) -> str:
        """Format a success message."""
        return f"✅ <b>{message}</b>"
    
    @staticmethod
    def error(message: str) -> str:
        """Format an error message."""
        return f"❌ <b>{message}</b>"
    
    @staticmethod
    def warning(message: str) -> str:
        """Format a warning message."""
        return f"⚠️ <b>{message}</b>"
    
    @staticmethod
    def info(message: str) -> str:
        """Format an info message."""
        return f"ℹ️ <b>{message}</b>"
    
    @staticmethod
    def leaderboard_entry(rank: int, name: str, value: Any, max_rank: int = 10) -> str:
        """Format a leaderboard entry with rank."""
        rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        rank_emoji = rank_emojis.get(rank, f"#{rank}")
        
        # Color code by rank
        if rank <= 3:
            return f"{rank_emoji} <b>{name}</b> <code>{value:,}</code>"
        elif rank <= 7:
            return f"{rank_emoji} {name} <code>{value:,}</code>"
        else:
            return f"{rank_emoji} {name} <i>{value:,}</i>"
    
    @staticmethod
    def progress_bar(current: int, maximum: int, width: int = 10) -> str:
        """Create a visual progress bar."""
        filled = int((current / maximum) * width)
        bar = "█" * filled + "░" * (width - filled)
        percentage = int((current / maximum) * 100)
        return f"[{bar}] {percentage}%"
    
    @staticmethod
    def inline_button(text: str, callback_data: str, emoji: str = "") -> InlineKeyboardButton:
        """Create an inline button with emoji."""
        button_text = f"{emoji} {text}".strip()
        return InlineKeyboardButton(button_text, callback_data=callback_data)
    
    @staticmethod
    def keyboard_grid(buttons: List[tuple], cols: int = 2) -> InlineKeyboardMarkup:
        """Create a grid keyboard from buttons list.
        Each button is (text, callback_data, emoji) tuple."""
        rows = []
        for i in range(0, len(buttons), cols):
            row = []
            for text, callback, emoji in buttons[i:i+cols]:
                row.append(RichFormatter.inline_button(text, callback, emoji))
            rows.append(row)
        return InlineKeyboardMarkup(rows)
    
    @staticmethod
    def format_balance(balance: int, currency_emoji: str = "🫧", currency_name: str = "Bubbles") -> str:
        """Format currency balance."""
        return f"<b>{currency_emoji} {balance:,} {currency_name}</b>"
    
    @staticmethod
    def format_time_remaining(seconds: float) -> str:
        """Format remaining time in human-readable format."""
        if seconds <= 0:
            return "Ready! ✅"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"⏱️ {hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"⏱️ {minutes}m {secs}s"
        else:
            return f"⏱️ {secs}s"
    
    @staticmethod
    def format_level(xp: int, level: int = None) -> str:
        """Format XP and level."""
        if level is None:
            level = xp // 1000
        next_level_xp = (level + 1) * 1000
        current_xp = xp % 1000
        bar = RichFormatter.progress_bar(current_xp, 1000, 15)
        return f"<b>Level {level}</b> {bar}\n<code>XP: {xp:,}</code>"
    
    @staticmethod
    def format_user_card(user_info: Dict[str, Any], currency_emoji: str = "🫧") -> str:
        """Format a user profile card."""
        name = user_info.get("first_name", "Unknown")
        balance = user_info.get("balance", 0)
        xp = user_info.get("xp", 0)
        status = user_info.get("status", "alive")
        kills = user_info.get("kills", 0)
        
        status_emoji = "✅" if status == "alive" else "💀"
        
        card = RichFormatter.header(f"Profile: {name}", "👤", "blue")
        card += f"\n{RichFormatter.stat_line('Balance', f'{balance:,} {currency_emoji}', '💰')}"
        card += f"\n{RichFormatter.stat_line('Status', status_emoji, '🎯')}"
        card += f"\n{RichFormatter.stat_line('XP', f'{xp:,}', '⭐')}"
        card += f"\n{RichFormatter.stat_line('Kills', kills, '⚔️')}"
        card += RichFormatter.footer()
        
        return card

# ---- Quick Format Helpers ----
def fmt_header(title: str) -> str:
    return RichFormatter.header(title)

def fmt_section(title: str) -> str:
    return RichFormatter.section(title)

def fmt_success(msg: str) -> str:
    return RichFormatter.success(msg)

def fmt_error(msg: str) -> str:
    return RichFormatter.error(msg)

def fmt_balance(balance: int, emoji: str = "🫧") -> str:
    return RichFormatter.format_balance(balance, emoji)

def fmt_time(seconds: float) -> str:
    return RichFormatter.format_time_remaining(seconds)
