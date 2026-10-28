
from django.contrib import admin
from .models import (
    UserProfile,
    Bin,
    WasteDisposal,
    CollectionAlert,
    SensorDepositEvent,
    RewardItem,
    RewardRedemption,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "points")
    list_filter = ("role",)
    search_fields = ("user__username", "phone")


@admin.register(Bin)
class BinAdmin(admin.ModelAdmin):
    list_display = (
        "bin_id", "name", "location", "fill_level", "is_active"
    )
    list_filter = ("is_active",)


@admin.register(WasteDisposal)
class WasteDisposalAdmin(admin.ModelAdmin):
    list_display = (
        "user", "bin", "selected_waste",
        "is_verified", "points_awarded", "created_at"
    )
    list_filter = ("is_verified", "selected_waste")
    search_fields = ("user__username", "bin__bin_id")


@admin.register(CollectionAlert)
class CollectionAlertAdmin(admin.ModelAdmin):
    list_display = ("bin", "fill_level", "is_collected", "created_at")
    list_filter = ("is_collected",)


@admin.register(SensorDepositEvent)
class SensorDepositEventAdmin(admin.ModelAdmin):
    list_display = ("event_key", "waste_type", "disposal", "created_at")
    search_fields = ("event_key",)


@admin.register(RewardItem)
class RewardItemAdmin(admin.ModelAdmin):
    list_display = ("name", "points_cost", "stock", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        "user", "reward", "points_spent",
        "coupon_code", "redeemed_at"
    )
    search_fields = ("user__username", "coupon_code")
    readonly_fields = (
        "user", "reward", "points_spent",
        "coupon_code", "redeemed_at"
    )
