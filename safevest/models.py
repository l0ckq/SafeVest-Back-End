from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# ============================
# USER CUSTOMIZADO (LOGIN POR EMAIL)
# ============================

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O usuário deve ter um email.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)

    # campos obrigatórios do Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # sem username

    objects = UserManager()

    def __str__(self):
        return self.email


# ============================
# EMPRESA
# ============================

class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    
    # Campos adicionais úteis
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nome']

    def __str__(self):
        return self.nome


# ============================
# SETOR
# ============================

class Setor(models.Model):
    nome = models.CharField(max_length=255)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="setores")
    
    # Campos adicionais
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ['empresa__nome', 'nome']
        # Evita setores duplicados na mesma empresa
        unique_together = [['empresa', 'nome']]

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"


# ============================
# PROFILE (administrador/supervisor/operador)
# ============================

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # MUDANÇA: empresa agora é obrigatória
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE,  # Se empresa é deletada, profile também
        related_name='profiles'
    )
    
    # Setor é opcional (nem todo profile precisa de setor)
    setor = models.ForeignKey(
        Setor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='profiles'
    )

    ROLE_CHOICES = (
        ("admin", "Administrador"),
        ("supervisor", "Supervisor"),
        ("operador", "Operador"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="operador")

    # Soft delete
    ativo = models.BooleanField(default=True)
    deletado = models.BooleanField(default=False)
    deletado_em = models.DateTimeField(null=True, blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.user.email} ({self.get_role_display()}) - {self.empresa.nome}"


# ============================
# VESTE
# ============================

class Veste(models.Model):
    numero_de_serie = models.CharField(max_length=255, unique=True, db_index=True)
    
    # MUDANÇA PRINCIPAL: Empresa agora é obrigatória e direta
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='vestes',
        help_text="Empresa proprietária da veste"
    )
    
    # MUDANÇA: Profile agora é opcional (veste pode existir sem estar atribuída)
    profile = models.ForeignKey(
        Profile, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='vestes',
        help_text="Operador atualmente usando a veste (opcional)"
    )

    # Setor da veste (independente do profile)
    setor = models.ForeignKey(
        Setor, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='vestes',
        help_text="Setor onde a veste opera"
    )
    
    # Metadados
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Veste"
        verbose_name_plural = "Vestes"
        ordering = ['numero_de_serie']
        indexes = [
            models.Index(fields=['numero_de_serie']),
            models.Index(fields=['empresa', 'ativa']),
        ]

    def __str__(self):
        status = f" → {self.profile.user.email}" if self.profile else " (disponível)"
        return f"Veste {self.numero_de_serie} - {self.empresa.nome}{status}"
    
    @property
    def esta_em_uso(self):
        """Verifica se a veste está atribuída a algum operador"""
        return self.profile is not None
    
    def atribuir_a(self, profile):
        """Atribui a veste a um profile e registra o uso"""
        if self.profile:
            raise ValueError(f"Veste já está em uso por {self.profile.user.email}")
        
        self.profile = profile
        self.save()
        
        # Cria registro de uso
        UsoVeste.objects.create(veste=self, profile=profile)
        
    def liberar(self):
        """Libera a veste e finaliza o registro de uso"""
        if not self.profile:
            raise ValueError("Veste não está em uso")
        
        # Finaliza último uso
        uso_ativo = UsoVeste.objects.filter(
            veste=self, 
            fim_uso__isnull=True
        ).first()
        
        if uso_ativo:
            from django.utils import timezone
            uso_ativo.fim_uso = timezone.now()
            uso_ativo.save()
        
        self.profile = None
        self.save()


# ============================
# USO DE VESTE (Histórico)
# ============================

class UsoVeste(models.Model):
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE, related_name='historico_usos')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='historico_vestes')

    inicio_uso = models.DateTimeField(auto_now_add=True)
    fim_uso = models.DateTimeField(null=True, blank=True)
    
    # Metadados adicionais
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Uso de Veste"
        verbose_name_plural = "Usos de Vestes"
        ordering = ['-inicio_uso']
        indexes = [
            models.Index(fields=['veste', 'inicio_uso']),
            models.Index(fields=['profile', 'inicio_uso']),
        ]

    def __str__(self):
        duracao = ""
        if self.fim_uso:
            delta = self.fim_uso - self.inicio_uso
            horas = delta.total_seconds() / 3600
            duracao = f" ({horas:.1f}h)"
        else:
            duracao = " (EM USO)"
        
        return f"{self.profile.user.email} → {self.veste.numero_de_serie}{duracao}"
    
    @property
    def duracao_uso(self):
        """Retorna duração do uso em segundos"""
        if not self.fim_uso:
            from django.utils import timezone
            return (timezone.now() - self.inicio_uso).total_seconds()
        return (self.fim_uso - self.inicio_uso).total_seconds()


# ============================
# LEITURA DE SENSORES
# ============================

class LeituraSensor(models.Model):
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE, related_name='leituras')

    bpm = models.IntegerField(help_text="Batimentos por minuto")
    temp = models.FloatField(help_text="Temperatura em °C")
    humi = models.FloatField(help_text="Umidade em %")
    mq2 = models.FloatField(help_text="Nível de gás MQ2")

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Leitura de Sensor"
        verbose_name_plural = "Leituras de Sensores"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['veste', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"Leitura {self.veste.numero_de_serie} ({self.timestamp.strftime('%d/%m/%Y %H:%M')})"
    
    @property
    def status(self):
        """Calcula status baseado no BPM"""
        if self.bpm > 160 or self.bpm < 50:
            return "Emergência"
        if self.bpm > 120 or self.bpm < 60:
            return "Alerta"
        return "Seguro"


# ============================
# ALERTAS
# ============================

class Alerta(models.Model):
    profile = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE,  # Se profile é deletado, alertas também
        related_name='alertas'
    )
    leitura_associada = models.ForeignKey(
        LeituraSensor, 
        on_delete=models.CASCADE,
        related_name='alertas'
    )

    TIPO_CHOICES = (
        ("Alerta", "Alerta"),
        ("Emergência", "Emergência"),
        ("Seguro", "Seguro"),
    )
    
    tipo_alerta = models.CharField(max_length=50, choices=TIPO_CHOICES)
    
    # Campos adicionais úteis
    resolvido = models.BooleanField(default=False)
    resolvido_em = models.DateTimeField(null=True, blank=True)
    resolvido_por = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='alertas_resolvidos'
    )
    observacoes = models.TextField(blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['profile', '-timestamp']),
            models.Index(fields=['resolvido', '-timestamp']),
        ]

    def __str__(self):
        status = "✓" if self.resolvido else "⚠"
        return f"{status} {self.tipo_alerta} - {self.profile.user.email} ({self.timestamp.strftime('%d/%m/%Y %H:%M')})"
    
    def resolver(self, usuario=None, observacao=None):
        """Marca alerta como resolvido"""
        from django.utils import timezone
        self.resolvido = True
        self.resolvido_em = timezone.now()
        self.resolvido_por = usuario
        if observacao:
            self.observacoes = observacao
        self.save()