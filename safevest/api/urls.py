from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import viewsets
from ..views import AlertaListCreate, VesteBulkCreateView, OnboardingView

# Cria o roteador para as views automáticas (CRUD)
router = DefaultRouter()
router.register(r'empresa', viewsets.EmpresaViewSet, basename='empresa')
router.register(r'setor', viewsets.SetorViewSet, basename='setor')
router.register(r'profile', viewsets.ProfileViewSet, basename='profile')
router.register(r'veste', viewsets.VesteViewSet, basename='veste')
router.register(r'usoveste', viewsets.UsoVesteViewSet, basename='usoveste')
router.register(r'leiturasensor', viewsets.LeituraSensorViewSet, basename='leiturasensor')

urlpatterns = [
    path('', include(router.urls)),
    
    path('alertas/', AlertaListCreate.as_view(), name='alerta-list-create'),
    path('vestes/bulk-create/', VesteBulkCreateView.as_view(), name='veste-bulk-create'),
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]