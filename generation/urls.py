from django.urls import path

from . import views

urlpatterns = [
    path("", views.GenerationCreateView.as_view()),
    path("refine-candidates/<int:candidate_id>/", views.SlotRefineCandidateDetailView.as_view()),
    path(
        "refine-candidates/<int:candidate_id>/apply/",
        views.SlotRefineCandidateApplyView.as_view(),
    ),
    path(
        "refine-candidates/<int:candidate_id>/discard/",
        views.SlotRefineCandidateDiscardView.as_view(),
    ),
    path("<int:job_id>/slots/<int:index>/refine/", views.SlotRefineCreateView.as_view()),
    path("<int:job_id>/", views.GenerationDetailView.as_view()),
    path("<int:job_id>/cancel/", views.GenerationCancelView.as_view()),
    path("<int:job_id>/stream/", views.GenerationStreamView.as_view()),
]
