from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("models/", views.ModelCatalogView.as_view(), name="models"),
    path("preferences/", views.PreferencesView.as_view(), name="preferences"),
    path("csrf/", views.csrf_cookie_view, name="csrf"),
    path("admin/pending-count/", views.AdminPendingCountView.as_view()),
    path("admin/pending-registrations/", views.AdminPendingRegistrationsView.as_view()),
    path("admin/pending-registrations/<int:user_id>/approve/", views.AdminRegistrationApproveView.as_view()),
    path("admin/pending-registrations/<int:user_id>/reject/", views.AdminRegistrationRejectView.as_view()),
    path("admin/users/", views.AdminUsersView.as_view()),
    path("admin/users/<int:user_id>/", views.AdminUserDetailView.as_view()),
]
