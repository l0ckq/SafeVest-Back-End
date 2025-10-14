import paho.mqtt.client as mqtt
import json
import requests
import os

# --- CONFIGURAÇÕES ---
# Centraliza as configurações para facilitar a manutenção.
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh"
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/dados_sensores"

# Endpoints da nossa API. Usar variáveis deixa o código mais limpo e fácil de alterar.
API_BASE_URL = "http://127.0.0.1:8000/api"
API_VESTES_ENDPOINT = f"{API_BASE_URL}/veste/"
API_LEITURAS_ENDPOINT = f"{API_BASE_URL}/leiturasensor/"
API_ALERTAS_ENDPOINT = f"{API_BASE_URL}/alertas/"


def on_connect(client, userdata, flags, rc, properties):
    """
    Função chamada quando o Cérebro se conecta ao broker.
    O objetivo é confirmar a conexão e se inscrever no tópico de interesse.
    """
    print(f"--- CÉREBRO CONECTADO! Resultado: {mqtt.connack_string(rc)} ---")
    client.subscribe(MQTT_TOPIC)
    print(f"--- OUVINDO o tópico: {MQTT_TOPIC} ---")

def on_message(client, userdata, msg):
    """
    Função principal, chamada a cada nova mensagem recebida do broker.
    Sua responsabilidade é processar o dado bruto, traduzi-lo em informações de negócio
    e interagir com a API para persistir os dados.
    """
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        print(f"<- Recebido: {data}")
        
        serial = data.get("numero_de_serie")
        if not serial:
            print("   |-> ERRO: Mensagem descartada por não conter 'numero_de_serie'.")
            return

        # 1. TRADUÇÃO: O Cérebro consulta a API para descobrir quem está usando a veste.
        # Este passo é crucial para desacoplar a identidade física (serial) da identidade lógica (IDs do banco).
        print(f"   |-> Consultando API para o serial {serial}...")
        response_veste = requests.get(f"{API_VESTES_ENDPOINT}?numero_de_serie={serial}")
        
        if not response_veste.ok or not response_veste.json():
            print(f"   |-> ERRO: Veste com serial '{serial}' não encontrada no banco de dados.")
            return
            
        veste_info = response_veste.json()[0]
        id_veste = veste_info.get("id_veste")
        id_usuario = veste_info.get("usuario")

        if not id_usuario:
            print(f"   |-> AVISO: Veste '{serial}' existe, mas não está associada a nenhum usuário no momento. Leitura descartada.")
            return

        print(f"   |-> Veste {id_veste} pertence ao Usuário {id_usuario}.")

        # 2. PERSISTÊNCIA: Prepara e salva a leitura bruta no banco de dados via API.
        leitura_payload = { "veste": id_veste, **data }
        response_leitura = requests.post(API_LEITURAS_ENDPOINT, json=leitura_payload)
        
        if not response_leitura.ok:
            print(f"   |-> ERRO ao salvar leitura! Status: {response_leitura.status_code}, Resposta: {response_leitura.text}")
            return

        leitura_salva = response_leitura.json()
        print(f"   |-> Leitura salva no DB! (ID: {leitura_salva.get('id_leitura')})")
        
        # 3. INTELIGÊNCIA: Aplica as regras de negócio para determinar o status.
        status_calculado = calcularStatus(data)
        print(f"   |-> Status Calculado: {status_calculado}")

        # 4. AÇÃO: Se o status for relevante, registra um Alerta formal no sistema.
        if status_calculado in ['Alerta', 'Emergência']:
            alerta_payload = {
                "usuario": id_usuario,
                "leitura_associada": leitura_salva.get('id_leitura'),
                "tipo_alerta": status_calculado
            }
            response_alerta = requests.post(API_ALERTAS_ENDPOINT, json=alerta_payload)
            if response_alerta.ok:
                print(f"   |-> ALERTA '{status_calculado}' registrado no DB com sucesso!")
            else:
                print(f"   |-> ERRO ao salvar alerta! Status: {response_alerta.status_code}, Resposta: {response_alerta.text}")

    except Exception as e:
        print(f"Ocorreu um erro geral ao processar a mensagem: {e}")

def calcularStatus(worker_data):
    """
    Centraliza as regras que definem o status de um trabalhador.
    Isso permite que as regras sejam alteradas em um único lugar, sem impactar o resto do sistema.
    """
    batimento = worker_data.get("batimento", 0)
    if batimento > 160 or batimento < 50: return 'Emergência'
    if batimento > 120 or batimento < 60: return 'Alerta'
    return 'Seguro'

# --- INICIALIZAÇÃO ---
# O ponto de entrada do serviço, responsável por configurar e iniciar a conexão.
print("Iniciando o Cérebro do SafeVest...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cerebro_service_main") 
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

print("Tentando conectar ao Broker...")
client.connect(BROKER_ADDRESS, BROKER_PORT)

# Inicia o loop que mantém o script rodando e ouvindo por mensagens indefinidamente.
client.loop_forever()