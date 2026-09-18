# ============================================================
# 🫧🦋 ʀuɴAk - Handler Registry
# ============================================================

from .start import register_start_handlers
from .moderation import register_moderation_handlers
from .locks import register_lock_handlers
from .welcome import register_welcome_handlers
from .economy import register_economy_handlers
from .pvp import register_pvp_handlers
from .levels import register_level_handlers
from .coupons import register_coupon_handlers
from .stickers import register_sticker_handlers
from .shop import register_shop_handlers
from .fun import register_fun_handlers
from .games import register_game_handlers
from .admin import register_admin_handlers
from .afk import register_afk_handlers
from .antiflood import register_antiflood_handlers
from .antispam import register_antispam_handlers
from .filters_plugin import register_filter_handlers
from .info import register_info_handlers
from .linkguard import register_linkguard_handlers
from .notes import register_notes_handlers
from .report import register_report_handlers
from .rules import register_rules_handlers
from .utility import register_utility_handlers


def register_all_handlers(app):
    register_start_handlers(app)
    register_moderation_handlers(app)
    register_lock_handlers(app)
    register_welcome_handlers(app)
    register_economy_handlers(app)
    register_pvp_handlers(app)
    register_level_handlers(app)
    register_coupon_handlers(app)
    register_sticker_handlers(app)
    register_shop_handlers(app)
    register_fun_handlers(app)
    register_game_handlers(app)
    register_admin_handlers(app)
    register_afk_handlers(app)
    register_antiflood_handlers(app)
    register_antispam_handlers(app)
    register_filter_handlers(app)
    register_info_handlers(app)
    register_linkguard_handlers(app)
    register_notes_handlers(app)
    register_report_handlers(app)
    register_rules_handlers(app)
    register_utility_handlers(app)
    print("✅ All ʀuɴAk handlers registered!")
