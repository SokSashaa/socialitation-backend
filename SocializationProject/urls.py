"""
URL configuration for SocializationProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

import socialize_main.urls
from SocializationProject import settings

schema_view = get_schema_view(
    openapi.Info(
        title="Soc API",
        default_version='v1'
    ),
    public=True,
    permission_classes=([permissions.AllowAny]),
)

urlpatterns = [path('api/admin/', admin.site.urls), path('doc/', schema_view.with_ui('swagger', cache_timeout=0)),
               path('api/obtain_token/', TokenObtainPairView.as_view(), name='authuser'),
               path('api/refresh_token/', TokenRefreshView.as_view(), name='refreshtoken'),
               path('api/schema/', SpectacularAPIView.as_view(), name='schema-customer'),
               path('api/schema-swagger/', SpectacularSwaggerView.as_view(url_name='schema-customer'),
                    name='schema-swagger'),
               path('api/auth/', include('rest_framework.urls')),
               ]

urlpatterns += socialize_main.urls.urlpatterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
