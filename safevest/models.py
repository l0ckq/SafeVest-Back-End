# safe_vest/models.py (Versão Corrigida)

from django.db import models

# O import do serializer aqui não é necessário e foi removido.
# from safevest.api.serializers import LeituraSensorSerializer 

class Empresa(models.Model):
    # ... seu modelo Empresa (sem alterações) ...
    cnpj = models.CharField(max_length=20, unique=True)
    nome_empresa = models.CharField(max_length=200)
    criado_em = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.nome_empresa

class Setor(models.Model):
    # ... seu modelo Setor (sem alterações) ...
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="setores")
    nome = models.CharField(max_length=200)
    def __str__(self):
        return f"{self.nome} - {self.empresa.nome_empresa}"

class Usuario(models.Model):
    # ... seu modelo Usuario (sem alterações) ...
    empresa = models.ForeignKey(Empresa, on_delete=models.DO_NOTHING, related_name="usuarios", null=True, blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="usuarios")
    id_usuario = models.AutoField(primary_key=True)
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.nome_completo

class Veste(models.Model):
    # ... seu modelo Veste (sem alterações) ...
    id_veste = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING)

class UsoVeste(models.Model):
    # ... seu modelo UsoVeste (sem alterações) ...
    id_uso = models.AutoField(primary_key=True)
    veste = models.ForeignKey(Veste, on_delete=models.DO_NOTHING)
    inicio_uso = models.DateTimeField()
    fim_uso = models.DateTimeField()

class LeituraSensor(models.Model):
    # ... seu modelo LeituraSensor (sem alterações) ...
    id_leitura = models.AutoField(primary_key=True)
    id_veste = models.ForeignKey(Veste, on_delete=models.DO_NOTHING)
    timestamp = models.DateTimeField()
    batimento = models.IntegerField()
    temperatura_A = models.DecimalField(max_digits=5, decimal_places=2)
    temperatura_C = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_co = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_bateria = models.DecimalField(max_digits=5, decimal_places=2)

# --- CORREÇÃO PRINCIPAL AQUI ---
class Alerta(models.Model):
    TIPO_ALERTA_CHOICES = [
        ('Alerta', 'Alerta'),
        ('Emergência', 'Emergência'),
    ]
    
    # CORREÇÃO 1: A relação é com o modelo 'Usuario', não 'Worker'.
    # O Cérebro enviará o ID do Usuario (worker_id).
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='alertas')
    
    # CORREÇÃO 2: A relação é com o modelo 'LeituraSensor', não com um serializer.
    leitura_associada = models.ForeignKey(LeituraSensor, on_delete=models.CASCADE)
    
    tipo_alerta = models.CharField(max_length=20, choices=TIPO_ALERTA_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        # Ajustado para usar 'usuario.nome_completo'
        return f"{self.tipo_alerta} para {self.usuario.nome_completo} em {self.timestamp.strftime('%d/%m/%Y %H:%M')}"