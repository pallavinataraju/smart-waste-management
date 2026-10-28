
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("collector", "Waste Collector"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    points = models.IntegerField(default=0)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="user"
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Bin(models.Model):
    bin_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    fill_level = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.bin_id


class WasteDisposal(models.Model):
    WASTE_CHOICES = [
        ("wet", "Wet Waste"),
        ("dry", "Dry Waste"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bin = models.ForeignKey(Bin, on_delete=models.CASCADE)

    selected_waste = models.CharField(
        max_length=10,
        choices=WASTE_CHOICES
    )

    sensor_result = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    is_verified = models.BooleanField(default=False)
    points_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.selected_waste}"


class CollectionAlert(models.Model):
    bin = models.ForeignKey(Bin, on_delete=models.CASCADE)
    fill_level = models.IntegerField()
    is_collected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bin.bin_id} - {self.fill_level}%"


class SensorDepositEvent(models.Model):
    event_key = models.CharField(max_length=100, unique=True)
    waste_type = models.CharField(max_length=10)

    disposal = models.ForeignKey(
        WasteDisposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_key


class RewardItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    points_cost = models.PositiveIntegerField()

    stock = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.points_cost} points"


class RewardRedemption(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reward_redemptions"
    )

    reward = models.ForeignKey(
        RewardItem,
        on_delete=models.PROTECT,
        related_name="redemptions"
    )

    points_spent = models.PositiveIntegerField()

    coupon_code = models.CharField(
        max_length=40,
        unique=True
    )

    redeemed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.reward.name}"
