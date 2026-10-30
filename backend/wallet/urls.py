from rest_framework.routers import DefaultRouter

from .views import BonusViewSet, TransactionViewSet, WalletViewSet

wallet_router = DefaultRouter(trailing_slash=False)
wallet_router.register("wallet", WalletViewSet, basename="wallet")
wallet_router.register("transactions", TransactionViewSet, basename="transactions")
wallet_router.register("bonus", BonusViewSet, basename="bonus")
