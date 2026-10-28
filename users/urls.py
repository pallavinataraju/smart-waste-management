
from django.urls import path
from . import views


urlpatterns = [
    path("register/", views.register, name="register"),

    path("login/", views.user_login, name="login"),

    path("bin/<str:bin_id>/", views.bin_detail, name="bin_detail"),

    path(
        "bin/<str:bin_id>/select/<str:waste_type>/",
        views.select_waste,
        name="select_waste",
    ),

    path(
        "sensor/<int:disposal_id>/",
        views.sensor_confirm,
        name="sensor_confirm",
    ),

    path(
        "bin/<str:bin_id>/fill/",
        views.update_fill_level,
        name="update_fill_level",
    ),

    path(
        "collector/",
        views.collector_dashboard,
        name="collector_dashboard",
    ),

    path(
        "collector/collect/<int:alert_id>/",
        views.mark_collected,
        name="mark_collected",
    ),

    path(
        "collector-dashboard/",
        views.collector_dashboard,
        name="collector_dashboard_alt",
    ),

    path(
        "collector/mark-collected/<int:alert_id>/",
        views.mark_collected,
        name="mark_collected_alt",
    ),

    path(
        "api/sensor-data/",
        views.receive_sensor_data,
        name="receive_sensor_data",
    ),

    path(
        "disposal/<int:disposal_id>/status/",
        views.disposal_status,
        name="disposal_status",
    ),

    path(
        "admin-dashboard/",
        views.admin_dashboard,
        name="admin_dashboard",
    ),

    path("rewards/", views.reward_store, name="reward_store"),

    path(
        "rewards/redeem/<int:reward_id>/",
        views.redeem_reward,
        name="redeem_reward",
    ),

    path("", views.home, name="home"),
]
