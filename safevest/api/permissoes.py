from rest_framework import permissions

class IsAdministrador(permissions.BasePermission):
    """
    Permite acesso apenas a usuários do grupo 'Administrador'.
    """
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.groups.filter(name="Administrador").exists()
        )


class IsSupervisor(permissions.BasePermission):
    """
    Permite acesso apenas a usuários do grupo 'Supervisor'.
    """
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.groups.filter(name="Supervisor").exists()
        )


class IsOperador(permissions.BasePermission):
    """
    Permite acesso apenas a usuários do grupo 'Operador'.
    """
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.groups.filter(name="Operador").exists()
        )


class IsSelfOrReadOnly(permissions.BasePermission):
    """
    Permite que o usuário edite apenas o próprio registro; 
    leitura liberada para métodos seguros (GET, HEAD, OPTIONS).
    """
    def has_object_permission(self, request, view, obj):
        return bool(
            obj == request.user or request.method in permissions.SAFE_METHODS
        )