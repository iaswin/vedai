# urls.py

from django.urls import path

from .views import (
    UploadView,
    StatusView,
    PageImageView,
    HealthView,
   
)

urlpatterns = [

    path(
        "upload/",
        UploadView.as_view(),
        name="upload",
    ),

    path(
        "status/<str:session_id>/",
        StatusView.as_view(),
        name="status",
    ),

    path(
        "image/<str:session_id>/<str:doc>/<int:page_num>/",
        PageImageView.as_view(),
        name="page-image",
    ),

    path(
        "health/",
        HealthView.as_view(),
        name="health",
    ),

]