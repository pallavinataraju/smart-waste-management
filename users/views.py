
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count
from django.contrib import messages
from django.utils.crypto import get_random_string

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import RewardItem


from .models import RewardItem, RewardRedemption

import json

from .forms import RegistrationForm
from .models import (
    UserProfile,
    Bin,
    WasteDisposal,
    CollectionAlert,
    SensorDepositEvent,
)


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            UserProfile.objects.get_or_create(user=user)
            login(request, user)

            return redirect("home")
    else:
        form = RegistrationForm()

    return render(
        request,
        "users/register.html",
        {"form": form},
    )


def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)

            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)

            return redirect("home")

        return render(
            request,
            "users/login.html",
            {"error": "Invalid username or password."},
        )

    return render(request, "users/login.html")



@login_required
def home(request):
    if request.user.is_superuser or request.user.is_staff:
        return redirect("admin_dashboard")

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    if profile.role == "collector":
        return redirect("collector_dashboard")

    disposals = WasteDisposal.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "users/home.html",
        {
            "profile": profile,
            "disposals": disposals,
            "verified_count": disposals.filter(
                is_verified=True
            ).count(),
            "total_points_earned": disposals.filter(
                is_verified=True
            ).aggregate(total=Sum("points_awarded"))["total"] or 0,
            "bins": Bin.objects.filter(is_active=True),
        },
    )



def bin_detail(request, bin_id):
    bin_record = get_object_or_404(Bin, bin_id=bin_id)
    all_bins = Bin.objects.all()

    return render(
        request,
        "users/bin_detail.html",
        {
            "bin": bin_record,
            "all_bins": all_bins,
        },
    )


def select_waste(request, bin_id, waste_type):
    if not request.user.is_authenticated:
        return redirect(f"/login/?next=/bin/{bin_id}/")

    bin_record = get_object_or_404(Bin, bin_id=bin_id)

    if waste_type not in ("wet", "dry", "metal"):
        return redirect("bin_detail", bin_id=bin_id)

    # Enforce the configured bin-to-waste mapping.
    if bin_id == "bin001" and waste_type != "wet":
        return redirect("bin_detail", bin_id=bin_id)

    if bin_id == "bin002" and waste_type != "dry":
        return redirect("bin_detail", bin_id=bin_id)

    disposal = WasteDisposal.objects.create(
        user=request.user,
        bin=bin_record,
        selected_waste=waste_type,
    )

    return render(
        request,
        "users/disposal_waiting.html",
        {
            "disposal": disposal,
            "bin": bin_record,
        },
    )


def sensor_confirm(request, disposal_id):
    if not request.user.is_authenticated:
        return redirect("login")

    disposal = get_object_or_404(
        WasteDisposal,
        id=disposal_id,
        user=request.user,
    )

    if disposal.is_verified:
        message = (
            f"Disposal verified. "
            f"{disposal.points_awarded} points awarded."
        )
    elif disposal.sensor_result:
        message = (
            "Disposal was not verified. "
            "No additional points were awarded."
        )
    else:
        message = (
            "Waiting for ESP32 verification. "
            "Points cannot be awarded through this URL."
        )

    return render(
        request,
        "users/sensor_result.html",
        {
            "disposal": disposal,
            "message": message,
        },
    )


def disposal_status(request, disposal_id):
    """Return the saved status and reward balance for the logged-in user."""
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Login required"},
            status=403,
        )

    disposal = get_object_or_404(
        WasteDisposal,
        id=disposal_id,
        user=request.user,
    )

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    return JsonResponse({
        "is_verified": disposal.is_verified,
        "points_awarded": disposal.points_awarded or 0,
        "sensor_result": (
            disposal.sensor_result.upper()
            if disposal.sensor_result
            else None
        ),
        "total_points": profile.points,
    })


def update_fill_level(request, bin_id):
    if request.method != "GET":
        return render(
            request,
            "users/fill_result.html",
            {"message": "Invalid request."},
        )

    try:
        fill_level = int(request.GET.get("level"))
    except (TypeError, ValueError):
        return render(
            request,
            "users/fill_result.html",
            {"message": "Invalid fill level."},
        )

    if not 0 <= fill_level <= 100:
        return render(
            request,
            "users/fill_result.html",
            {"message": "Fill level must be between 0 and 100."},
        )

    bin_record = get_object_or_404(Bin, bin_id=bin_id)

    bin_record.fill_level = fill_level
    bin_record.save(update_fields=["fill_level"])

    if fill_level >= 80:
        if not CollectionAlert.objects.filter(
            bin=bin_record,
            is_collected=False,
        ).exists():
            CollectionAlert.objects.create(
                bin=bin_record,
                fill_level=fill_level,
            )

        message = (
            f"ALERT: {bin_record.bin_id} is "
            f"{fill_level}% full. Collection required."
        )
    else:
        message = (
            f"{bin_record.bin_id} fill level updated "
            f"to {fill_level}%. No collection required."
        )

    return render(
        request,
        "users/fill_result.html",
        {
            "message": message,
            "bin": bin_record,
        },
    )


@login_required
def collector_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    if not (
        request.user.is_staff
        or request.user.is_superuser
        or profile.role == "collector"
    ):
        return redirect("home")

    alerts = CollectionAlert.objects.filter(
        is_collected=False
    ).select_related("bin").order_by("-created_at")

    collection_history = CollectionAlert.objects.filter(
        is_collected=True
    ).select_related("bin").order_by("-created_at")[:20]

    return render(
        request,
        "users/collector_dashboard.html",
        {
            "alerts": alerts,
            "collection_history": collection_history,
        },
    )


@login_required
@require_POST
def mark_collected(request, alert_id):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    if not (
        request.user.is_staff
        or request.user.is_superuser
        or profile.role == "collector"
    ):
        return redirect("home")

    with transaction.atomic():
        alert = get_object_or_404(
            CollectionAlert.objects.select_for_update(),
            id=alert_id,
        )

        if not alert.is_collected:
            alert.is_collected = True
            alert.save(update_fields=["is_collected"])

            bin_record = alert.bin
            bin_record.fill_level = 0
            bin_record.save(update_fields=["fill_level"])

    return redirect("collector_dashboard")

@csrf_exempt
@require_POST
def receive_sensor_data(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    def valid_fill(value):
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value <= 100
        )

    wet_fill = data.get("wet_bin_fill_percent")
    dry_fill = data.get("dry_bin_fill_percent")

    if wet_fill is not None and not valid_fill(wet_fill):
        return JsonResponse(
            {"error": "Invalid wet-bin fill"},
            status=400,
        )

    if dry_fill is not None and not valid_fill(dry_fill):
        return JsonResponse(
            {"error": "Invalid dry-bin fill"},
            status=400,
        )

    with transaction.atomic():
        try:
            wet_bin = Bin.objects.get(bin_id="bin001")
            dry_bin = Bin.objects.get(bin_id="bin002")
        except Bin.DoesNotExist:
            return JsonResponse(
                {"error": "Create bin001 and bin002 in Django Admin"},
                status=404,
            )

        # Update valid bin-fill readings.
        for bin_record, fill in (
            (wet_bin, wet_fill),
            (dry_bin, dry_fill),
        ):
            if fill is None:
                continue

            bin_record.fill_level = fill
            bin_record.save(update_fields=["fill_level"])

            if (
                fill >= 80
                and not CollectionAlert.objects.filter(
                    bin=bin_record,
                    is_collected=False,
                ).exists()
            ):
                CollectionAlert.objects.create(
                    bin=bin_record,
                    fill_level=fill,
                )

        reward_message = "No deposit event processed"
        points_awarded = 0

        is_event = data.get("deposit_verified") is True
        event_id = data.get("deposit_event_id")
        waste_type = data.get("waste_type")

        if is_event:
            if (
                not isinstance(event_id, int)
                or isinstance(event_id, bool)
                or event_id < 1
                or waste_type not in ("WET", "DRY")
            ):
                return JsonResponse(
                    {"error": "Invalid deposit event data"},
                    status=400,
                )

            # Prevent processing the same event ID twice.
            # Note: the ESP32 counter may restart after a reboot.
            event_key = f"esp32-{event_id}"

            existing_event = SensorDepositEvent.objects.filter(
                event_key=event_key
            ).first()

            if existing_event:
                reward_message = "Duplicate event ignored"
            else:
                expected_bin = (
                    wet_bin if waste_type == "WET" else dry_bin
                )
                expected_type = waste_type.lower()

                # Match the newest pending disposal for this bin/type.
                disposal = (
                    WasteDisposal.objects.select_for_update()
                    .filter(
                        bin=expected_bin,
                        selected_waste=expected_type,
                        is_verified=False,
                    )
                    .order_by("-created_at", "-id")
                    .first()
                )

                if disposal is None:
                    reward_message = (
                        "Event received, but no matching pending "
                        "disposal exists. No points awarded."
                    )
                else:
                    # Record the event and award points atomically.
                    SensorDepositEvent.objects.create(
                        event_key=event_key,
                        waste_type=waste_type,
                        disposal=disposal,
                    )

                    profile, _ = UserProfile.objects.get_or_create(
                        user=disposal.user
                    )

                    points = 5
                    profile.points += points
                    profile.save(update_fields=["points"])

                    disposal.is_verified = True
                    disposal.sensor_result = expected_type
                    disposal.points_awarded = points
                    disposal.save(
                        update_fields=[
                            "is_verified",
                            "sensor_result",
                            "points_awarded",
                        ]
                    )

                    points_awarded = points
                    reward_message = (
                        f"Disposal verified; {points} points awarded"
                    )

        return JsonResponse({
            "message": "Sensor data received",
            "wet_bin": {
                "bin_id": wet_bin.bin_id,
                "fill_level": wet_bin.fill_level,
            },
            "dry_bin": {
                "bin_id": dry_bin.bin_id,
                "fill_level": dry_bin.fill_level,
            },
            "deposit_event": reward_message,
            "points_awarded": points_awarded,
        })

@login_required
def admin_dashboard(request):
    if not (
        request.user.is_staff or request.user.is_superuser
    ):
        return redirect("home")

    profiles = UserProfile.objects.select_related("user")

    context = {
        "user_count": UserProfile.objects.filter(
            role="user"
        ).count(),
        "collector_count": UserProfile.objects.filter(
            role="collector"
        ).count(),
        "bin_count": Bin.objects.count(),
        "active_bin_count": Bin.objects.filter(
            is_active=True
        ).count(),
        "disposal_count": WasteDisposal.objects.count(),
        "verified_disposal_count": WasteDisposal.objects.filter(
            is_verified=True
        ).count(),
        "points_awarded": WasteDisposal.objects.filter(
            is_verified=True
        ).aggregate(total=Sum("points_awarded"))["total"] or 0,
        "pending_alerts": CollectionAlert.objects.filter(
            is_collected=False
        ).select_related("bin").order_by("-created_at"),
        "recent_disposals": WasteDisposal.objects.select_related(
            "user", "bin"
        ).order_by("-created_at")[:10],
        "profiles": profiles.order_by("user__username")[:50],
        "rewards": RewardItem.objects.all().order_by("name"),
    }

    return render(
        request,
        "users/admin_dashboard.html",
        context,
    )

@login_required
def reward_store(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    rewards = RewardItem.objects.filter(
        is_active=True,
        stock__gt=0,
    ).order_by("points_cost")

    redemptions = RewardRedemption.objects.filter(
        user=request.user
    ).select_related("reward").order_by("-redeemed_at")

    return render(
        request,
        "users/reward_store.html",
        {
            "profile": profile,
            "rewards": rewards,
            "redemptions": redemptions,
        },
    )


@login_required
@require_POST
def redeem_reward(request, reward_id):
    try:
        with transaction.atomic():
            profile, _ = UserProfile.objects.get_or_create(
                user=request.user
            )

            # Lock the rows where supported by the database.
            profile = UserProfile.objects.select_for_update().get(
                pk=profile.pk
            )

            reward = get_object_or_404(
                RewardItem.objects.select_for_update(),
                pk=reward_id,
                is_active=True,
            )

            if reward.stock < 1:
                messages.error(request, "This reward is out of stock.")
                return redirect("reward_store")

            if profile.points < reward.points_cost:
                messages.error(
                    request,
                    "You do not have enough reward points."
                )
                return redirect("reward_store")

            profile.points -= reward.points_cost
            profile.save(update_fields=["points"])

            reward.stock -= 1
            reward.save(update_fields=["stock"])

            coupon_code = (
                "ECO-" + get_random_string(12).upper()
            )

            RewardRedemption.objects.create(
                user=request.user,
                reward=reward,
                points_spent=reward.points_cost,
                coupon_code=coupon_code,
            )

    except Exception:
        # Unexpected errors should be logged during deployment.
        # Re-raise them rather than silently hiding database failures.
        raise

    messages.success(
        request,
        f"Reward redeemed successfully! Your code is {coupon_code}"
    )
    return redirect("reward_store")


@login_required
def reward_redemption_history(request):
    redemptions = RewardRedemption.objects.filter(
        user=request.user
    ).select_related("reward").order_by("-redeemed_at")

    return render(
        request,
        "users/reward_redemption_history.html",
        {
            "redemptions": redemptions,
        },
    )
