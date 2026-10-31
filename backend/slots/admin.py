from django.contrib import admin

from base.admin import ImagePreviewMixin
from wallet.admin import ReadOnlyAdmin
from .models import SlotSound, SlotSpin, SlotSymbol, SlotSymbolName, ZeusPageLabel


class SlotSymbolNameInline(admin.TabularInline):
    model = SlotSymbolName
    extra = 0


@admin.register(SlotSymbol)
class SlotSymbolAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ["code", "order", "image_preview"]
    inlines = [SlotSymbolNameInline]


@admin.register(SlotSymbolName)
class SlotSymbolNameAdmin(admin.ModelAdmin):
    list_display = ["name", "symbol", "lang"]
    list_filter = ["lang"]


@admin.register(SlotSound)
class SlotSoundAdmin(admin.ModelAdmin):
    list_display = ["code", "file", "is_active"]
    list_filter = ["is_active"]


@admin.register(ZeusPageLabel)
class ZeusPageLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "game_title", "spin"]
    list_filter = ["lang"]


@admin.register(SlotSpin)
class SlotSpinAdmin(ReadOnlyAdmin):
    list_display = ["user", "game", "cost", "bonus_buy", "payout", "jackpot_tier", "created_at"]
    list_filter = ["game", "bonus_buy", "jackpot_tier"]
    search_fields = ["user__email"]
