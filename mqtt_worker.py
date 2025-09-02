import os
import sys
import json
import django
import paho.mqtt.client as mqtt
import ssl  # Necessário para a configuração TLS

# --- CONFIGURAÇÃO DO DJANGO ---
# Garante que o script possa encontrar e usar os componentes do seu projeto.
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setup.settings") # ATENÇÃO: Mude 'projeto_veste' se o nome do seu projeto for outro
django.setup()

# --- IMPORTAÇÃO DE MODELOS DJANGO ---
# Importe seus modelos APÓS a inicialização do Django.
# Assumindo que seu app se chama 'core' e o modelo 'DadosSensor'.
from safevest.models import LeituraSensor

# --- CONFIGURAÇÕES DO MQTT (Extraídas das suas imagens) ---
MQTT_BROKER = "jaragua.lmq.cloudamqp.com"
MQTT_PORT = 1883  # Porta segura (TLS)
MQTT_USER = "qyyguyzh:qyyguyzh"
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "vest"
  # << IMPORTANTE: Defina o tópico que será usado!

# --- FUNÇÕES DE CALLBACK MQTT ---

def on_connect(client, userdata, flags, rc):
    """Callback chamado quando o cliente se conecta ao broker."""
    if rc == 0:
        print("Conectado ao Broker MQTT (CloudAMQP) com sucesso!")
        client.subscribe(MQTT_TOPIC)
        print(f"Inscrito no tópico: {MQTT_TOPIC}")
    else:
        print(f"Falha ao conectar, código de retorno: {rc}\nVerifique as credenciais e a conexão de rede.")

def on_message(client, userdata, msg):
    """Callback chamado quando uma mensagem é recebida do broker."""
    print(f"Mensagem recebida no tópico '{msg.topic}'")

    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        print(f"Payload (JSON): {payload}")

        

        # Assumindo que seu modelo 'DadosSensor' tem estes campos
        # e que o JSON enviado pela veste tem estas chaves.
        LeituraSensor.objects.create(
            id_veste=payload['id_veste'],
            timestamp=payload['timestamp'],
            batimentos_cardiacos=payload['batimento'],
            temperatura_corporal=payload['temperatura_A'],
            temperatura_ambiente=payload['temperatura_C'],
            nivel_co=payload['nivel_co'],
            nivel_bateria=payload['nivel_bateria']
        )
        print(">> Dados salvos no banco de dados com sucesso!")

    except json.JSONDecodeError:
        print("Erro: A mensagem recebida não é um JSON válido.")
    except KeyError as e:
        print(f"Erro: A chave {e} não foi encontrada no JSON recebido.")
    except Exception as e:
        print(f"Erro inesperado ao processar a mensagem: {e}")


# --- FUNÇÃO PRINCIPAL ---
def main():
    client = mqtt.Client(client_id=f"django_worker_{os.getpid()}") # Cria um ID de cliente único

    # Configura o usuário e senha para autenticação
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    # Configura o TLS para uma conexão segura
    #client.tls_set(tls_version=ssl.PROTOCOL_TLS)

    # Atribui as funções de callback
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Conectando ao broker {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Inicia o loop que mantém o cliente rodando e escutando por mensagens.
    client.loop_forever()

if __name__ == '__main__':
    main()