import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from django.contrib.auth.models import User
from django.db.models import Count
from safevest.models import Profile

def limpar_emails_duplicados():
    print("🔍 Buscando usuários duplicados por email...")
    
    # Encontrar emails com múltiplos usuários
    duplicate_emails = User.objects.values('email')\
        .annotate(count=Count('id'))\
        .filter(count__gt=1)
    
    if not duplicate_emails:
        print("✅ Nenhuma duplicata encontrada!")
        return
    
    total_deleted = 0
    
    for dup in duplicate_emails:
        email = dup['email']
        if not email:  # Pular emails vazios
            continue
            
        users = User.objects.filter(email=email).order_by('-date_joined', '-id')
        
        print(f"\n📧 Processando: {email} ({dup['count']} usuários)")
        
        # Verificar quais usuários têm profiles
        users_with_profiles = []
        users_without_profiles = []
        
        for user in users:
            try:
                profile = user.profile  # Graças ao related_name do OneToOneField
                users_with_profiles.append((user, profile))
            except Profile.DoesNotExist:
                users_without_profiles.append(user)
        
        # Lógica de decisão para qual manter
        if users_with_profiles:
            # Priorizar usuários que têm profile
            keeper_user, keeper_profile = users_with_profiles[0]
            print(f"✅ Mantendo (com profile): {keeper_user.username} (ID: {keeper_user.id})")
            
            # Excluir outros usuários com profile
            for user, profile in users_with_profiles[1:]:
                print(f"🗑️  Excluindo usuário com profile: {user.username} (ID: {user.id})")
                user.delete()
                total_deleted += 1
            
            # Excluir usuários sem profile
            for user in users_without_profiles:
                print(f"🗑️  Excluindo usuário sem profile: {user.username} (ID: {user.id})")
                user.delete()
                total_deleted += 1
                
        else:
            # Se nenhum tem profile, manter o mais recente
            keeper_user = users.first()
            print(f"✅ Mantendo (mais recente): {keeper_user.username} (ID: {keeper_user.id})")
            
            # Excluir os demais
            for user in users[1:]:
                print(f"🗑️  Excluindo: {user.username} (ID: {user.id})")
                user.delete()
                total_deleted += 1
    
    print(f"\n🎯 Limpeza concluída! {total_deleted} usuário(s) excluído(s)")

if __name__ == "__main__":
    limpar_emails_duplicados()