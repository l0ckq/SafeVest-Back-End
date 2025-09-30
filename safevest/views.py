from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Alerta, Veste
from .api import serializers  

class AlertaListCreate(generics.ListCreateAPIView):
    queryset = Alerta.objects.all()
    serializer_class = serializers.AlertaSerializer
    
class VesteBulkCreateView(APIView):
    """
    View para criar múltiplas Vestes de uma só vez a partir de uma lista de números de série.
    """
    def post(self, request, *args, **kwargs):
        # Pega a lista de seriais do corpo da requisição.
        # Esperamos um JSON como: { "seriais": ["SV-001", "SV-002", ...] }
        seriais = request.data.get('seriais', [])

        if not isinstance(seriais, list) or not seriais:
            return Response(
                {"erro": "A chave 'seriais' deve ser uma lista não-vazia."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Contadores e listas para o nosso feedback detalhado
        criadas_count = 0
        ignoradas_count = 0
        seriais_criados = []
        seriais_ignorados = []

        # Itera sobre cada serial recebido
        for serial in seriais:
            serial_limpo = serial.strip() # Limpa espaços em branco
            if not serial_limpo:
                continue
            
            # get_or_create() é a mágica do Django:
            # Ele tenta encontrar uma Veste com este serial.
            # Se encontrar, ele a retorna. Se NÃO encontrar, ele a CRIA.
            # A variável 'created' nos diz se foi criada (True) ou se já existia (False).
            veste, created = Veste.objects.get_or_create(
                numero_de_serie=serial_limpo,
                # Podemos definir valores padrão para novos coletes aqui, se necessário
                defaults={'usuario': None} 
            )

            if created:
                criadas_count += 1
                seriais_criados.append(serial_limpo)
            else:
                ignoradas_count += 1
                seriais_ignorados.append(serial_limpo)
        
        # Monta a resposta detalhada para o front-end
        feedback = {
            "mensagem": f"Processamento concluído: {criadas_count} vestes criadas, {ignoradas_count} já existiam.",
            "criadas": seriais_criados,
            "ignoradas": seriais_ignorados
        }
        
        return Response(feedback, status=status.HTTP_201_CREATED)