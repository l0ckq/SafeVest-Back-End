from django.contrib import admin
from django.urls import path, include
from rest_framework import routers, permissions
from rest_framework_simplejwt.views import TokenRefreshView
from safevest.api.authentication import EmailTokenObtainPairView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from safevest.api import viewsets
from safevest.views import (
    AlertaListCreate,
    VesteBulkCreateView,
    UserByEmailView,
    OnboardingView,
    buscar_veste_por_serial,
    signup_empresa_admin,
    criar_usuario_colaborador,
    listar_usuarios_empresa,
    usuario_detalhe,
    perfil_usuario,
    listar_setores_empresa,
    dashboard_estatisticas,
    upload_foto_perfil,
)

# --- Swagger docs ---
schema_view = get_schema_view(
    openapi.Info(
        title="SafeVest API",
        default_version='v1',
        description="Sistema para controle de dados dos coletes SafeVest.",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# --- DRF Routers ---
router = routers.DefaultRouter()
router.register(r'empresa', viewsets.EmpresaViewSet, basename='empresa')
router.register(r'setor', viewsets.SetorViewSet, basename='setor')
router.register(r'profile', viewsets.ProfileViewSet, basename='profile')
router.register(r'veste', viewsets.VesteViewSet, basename='veste')
router.register(r'usoveste', viewsets.UsoVesteViewSet, basename='usoveste')
router.register(r'leiturasensor', viewsets.LeituraSensorViewSet, basename='leiturasensor')

# --- Rotas principais ---
api_patterns = [
    # Rotas automáticas via router
    path('', include(router.urls)),

    # --- AUTENTICAÇÃO ---
    path('token/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # --- CADASTRO ---
    path('signup/', signup_empresa_admin, name='signup-empresa-admin'),
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('usuarios/create/', criar_usuario_colaborador, name='criar-usuario'),

    # --- GESTÃO DE USUÁRIOS ---
    path('usuarios/', listar_usuarios_empresa, name='listar-usuarios'),
    path('usuarios/<int:user_id>/', usuario_detalhe, name='usuario-detalhe'),
    path('usuarios/por-email/', UserByEmailView.as_view(), name='user-by-email'),
    path('perfil/', perfil_usuario, name='perfil-usuario'),

    # --- EMPRESA ---
    path('setores/', listar_setores_empresa, name='listar-setores'),

    # --- VESTES ---
    path('vestes/bulk-create/', VesteBulkCreateView.as_view(), name='veste-bulk-create'),
    path('vestes/buscar/', buscar_veste_por_serial, name='buscar-veste'),

    # --- DASHBOARD / UTILITÁRIOS ---
    path('dashboard/', dashboard_estatisticas, name='dashboard'),
    path('upload-foto/', upload_foto_perfil, name='upload-foto'),

    # --- ALERTAS ---
    path('alertas/', AlertaListCreate.as_view(), name='alerta-list-create'),
]

# --- URL Principal ---
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_patterns)),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]