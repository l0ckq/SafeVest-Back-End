from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from django.db import transaction
from .models import Empresa, Setor, Profile, Veste, UsoVeste, LeituraSensor, Alerta
from .api import serializers

class OnboardingView(APIView):
    permission_classes = []
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        nome_empresa = request.data.get('nome_empresa')
        cnpj = request.data.get('cnpj')
        nome_admin = request.data.get('nome_admin')
        email_admin = request.data.get('email_admin')
        senha_admin = request.data.get('senha_admin')

        if not all([nome_empresa, cnpj, nome_admin, email_admin, senha_admin]):
            return Response({"erro": "Todos os campos são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)
        
        nova_empresa = Empresa.objects.create(nome_empresa=nome_empresa, cnpj=cnpj)
        
        primeiro_admin_user = User.objects.create_user(
            username=email_admin, email=email_admin, password=senha_admin, first_name=nome_admin
        )
        
        Profile.objects.create(user=primeiro_admin_user, empresa=nova_empresa)
        
        admin_group, _ = Group.objects.get_or_create(name=f"admin_{nova_empresa.id}")
        primeiro_admin_user.groups.add(admin_group)

        return Response({"sucesso": "Empresa e admin criados com sucesso!"}, status=status.HTTP_201_CREATED)

class VesteBulkCreateView(APIView):
    def post(self, request, *args, **kwargs):
        seriais = request.data.get('seriais', [])
        # ... (lógica de validação) ...
        criadas_count, ignoradas_count = 0, 0
        seriais_criados, seriais_ignorados = [], []
        
        for serial in seriais:
            serial_limpo = serial.strip()
            if not serial_limpo: continue
            _, created = Veste.objects.get_or_create(
                numero_de_serie=serial_limpo, defaults={'profile': None}
            )
            if created:
                criadas_count += 1
                seriais_criados.append(serial_limpo)
            else:
                ignoradas_count += 1
                seriais_ignorados.append(serial_limpo)
        
        feedback = { "mensagem": f"{criadas_count} criadas, {ignoradas_count} ignoradas.", "criadas": seriais_criados, "ignoradas": seriais_ignorados }
        return Response(feedback, status=status.HTTP_201_CREATED)

class AlertaListCreate(generics.ListCreateAPIView):
    queryset = Alerta.objects.all()
    serializer_class = serializers.AlertaSerializer