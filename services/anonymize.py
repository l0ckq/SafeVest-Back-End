from django.utils import timezone
import hashlib

def anonymize_user(user, profile):
    """
    Anonimiza campos sensíveis do user e do profile.
    Mantém um campo interno (username -> EXCLUIDO-<hash>) para auditoria.
    """
    ts = timezone.now().isoformat()
    seed = f"{user.id}-{ts}"
    digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]

    # Anonimizar User
    user.email = f"excluido+{digest}@example.invalid"
    user.username = f"excluido-{digest}"
    user.first_name = "EXCLUIDO"
    user.last_name = ""
    user.is_active = False
    user.save(update_fields=['email', 'username', 'first_name', 'last_name', 'is_active'])

    # Anonimizar Profile (ajuste campos conforme seu model)
    profile.deletado = True
    profile.ativo = False
    # se tiver campos sensíveis no profile:
    if hasattr(profile, 'telefone'):
        profile.telefone = None
    if hasattr(profile, 'cpf'):
        profile.cpf = None
    profile.save()
