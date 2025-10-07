from django.contrib import admin
from django.urls import path, include
from safevest.api import viewsets
from safevest.views import AlertaListCreate, VesteBulkCreateView, OnboardingView
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

schema_view = get_schema_view(...)

route = routers.DefaultRouter()
route.register(r'empresa', viewsets.EmpresaViewSet)
route.register(r'setor', viewsets.SetorViewSet)
route.register(r'profile', viewsets.ProfileViewSet) # Agora usamos Profile
route.register(r'veste', viewsets.VesteViewSet)
route.register(r'usoveste', viewsets.UsoVesteViewSet)
route.register(r'leiturasensor', viewsets.LeituraSensorViewSet)

api_urlpatterns = [
    path('', include(route.urls)),
    path('alertas/', AlertaListCreate.as_view(), name='alerta-list-create'),
    path('vestes/bulk-create/', VesteBulkCreateView.as_view(), name='veste-bulk-create'),
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/', include(api_urlpatterns)),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)