from rest_framework.routers import DefaultRouter

from .views import (
    SlotSoundViewSet,
    SlotSpinViewSet,
    SlotSymbolNameViewSet,
    SlotSymbolViewSet,
    ZeusPageLabelViewSet,
)

slots_router = DefaultRouter(trailing_slash=False)
slots_router.register("slot_spins", SlotSpinViewSet, basename="slot_spins")
slots_router.register("slot_symbols", SlotSymbolViewSet, basename="slot_symbols")
slots_router.register("slot_symbol_names", SlotSymbolNameViewSet, basename="slot_symbol_names")
slots_router.register("slot_sounds", SlotSoundViewSet, basename="slot_sounds")
slots_router.register("zeus_page_labels", ZeusPageLabelViewSet, basename="zeus_page_labels")
