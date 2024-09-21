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
from django.contrib import admin
from django.templatetags.static import static
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularSwaggerView
from django.conf.urls.static import static


import socialize_main.urls
from SocializationProject import settings

schema_view = get_schema_view(
    openapi.Info(
        title="Soc API",
        default_version='v1'
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('doc/', schema_view.with_ui('swagger', cache_timeout=0))
]

urlpatterns.append(path('obtain_token/', TokenObtainPairView.as_view(), name='authuser'))
urlpatterns.append(path('refresh_token/', TokenRefreshView.as_view(), name='refreshtoken'))


urlpatterns.append(path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema-customer'), name='swagger-ui'))

urlpatterns += socialize_main.urls.urlpatterns


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
