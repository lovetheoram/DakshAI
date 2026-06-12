
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/syllabus/", include("syllabus.urls")),
    path("api/quiz/", include("quiz.urls")),
    path("api/progress/", include("progress.urls")),
    path("api/social/", include("social.urls")),
    path("auth/", include("authapp.urls")),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
