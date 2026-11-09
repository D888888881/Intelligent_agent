from django.urls import path

from . import views

urlpatterns = [
    path("conversations/", views.ConversationListCreateView.as_view()),
    path("conversations/<int:pk>/", views.ConversationDetailView.as_view()),
    path("conversations/<int:pk>/share/", views.ConversationShareView.as_view()),
    path("conversations/<int:pk>/messages/", views.MessageListView.as_view()),
    path("conversations/<int:pk>/chat/stream/", views.ChatStreamView.as_view()),
    path("shareable-users/", views.ShareableUsersView.as_view()),
]
