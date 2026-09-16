# ============================================================
# 🫧🦋 ʀuɴAk - Handler Registry
# ============================================================

from .start import register_start_handlers
from .moderation import register_moderation_handlers
from .locks import register_lock_handlers
from .welcome import register_welcome_handlers
from .economy import register_economy_handlers
from .shop import register_shop_handlers
from .fun import register_fun_handlers
from .games import register_game_handlers
from .admin import register_admin_handlers


def register_all_handlers(app):
    register_start_handlers(app)
    register_moderation_handlers(app)
    register_lock_handlers(app)
    register_welcome_handlers(app)
    register_economy_handlers(app)
    register_shop_handlers(app)
    register_fun_handlers(app)
    register_game_handlers(app)
    register_admin_handlers(app)
    print("✅ All ʀuɴAk handlers registered!")
