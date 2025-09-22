import paho.mqtt.client as mqtt
import json
import requests
import os

# --- CREDENCIAIS FINAIS --- #
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh" # <<< A CORREÇÃO ESTÁ AQUI
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/dados_sensores"

API_LEITURAS = "http://127.0.0.1:8000/api/leiturasensor/"
API_ALERTAS = "http://127.0.0.1:8000/api/alertas/"

def on_log(client, userdata, level, buf):
    print(f"[LOG]: {buf}")

def on_connect(client, userdata, flags, rc, properties):
    print(f"--- CONECTADO! Resultado: {mqtt.connack_string(rc)} ---")
    client.subscribe(MQTT_TOPIC)
    print(f"--- OUVINDO o tópico: {MQTT_TOPIC} ---")

def on_disconnect(client, userdata, flags, rc, properties):
    print(f"--- DESCONECTADO do Broker! Código: {rc} ---")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        print(f"<- Recebido: {data}")
        
        leitura_payload = {
            "id_veste": data.get("id_veste"),
            "timestamp": data.get("timestamp"),
            "batimento": data.get("batimento"),
            "temperatura_A": data.get("temperatura_A"),
            "temperatura_C": data.get("temperatura_C"),
            "nivel_co": data.get("nivel_co"),
            "nivel_bateria": data.get("nivel_bateria")
        }
        
        print(f"   |-> Enviando para {API_LEITURAS}...")
        response = requests.post(API_LEITURAS, json=leitura_payload)
        
        if not response.ok:
            print(f"   |-> ERRO ao salvar leitura! Status: {response.status_code}, Resposta: {response.text}")
            return

        leitura_salva = response.json()
        print(f"   |-> Leitura salva no DB! (ID: {leitura_salva.get('id_leitura')})")
        
        status_calculado = calcularStatus(data)
        print(f"   |-> Status Calculado: {status_calculado}")

        if status_calculado in ['Alerta', 'Emergência']:
            alerta_payload = {
                "usuario": data.get("id_usuario"),
                "leitura_associada": leitura_salva.get('id_leitura'),
                "tipo_alerta": status_calculado
            }
            print(f"   |-> Enviando para {API_ALERTAS}...")
            response_alerta = requests.post(API_ALERTAS, json=alerta_payload)
            if response_alerta.ok:
                print(f"   |-> ALERTA '{status_calculado}' registrado no DB com sucesso!")
            else:
                print(f"   |-> ERRO ao salvar alerta! Status: {response_alerta.status_code}, Resposta: {response_alerta.text}")

    except requests.exceptions.ConnectionError:
        print("\n   |-> ERRO DE CONEXÃO: Não foi possível conectar à API Django. O servidor está rodando?")
    except Exception as e:
        print(f"Ocorreu um erro geral ao processar a mensagem: {e}")


def calcularStatus(worker_data):
    batimento = worker_data.get("batimento", 0)
    if batimento > 160 or batimento < 50: return 'Emergência'
    if batimento > 120 or batimento < 60: return 'Alerta'
    return 'Seguro'

print("Iniciando o Cérebro do SafeVest...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cerebro_service_main") 
client.on_log = on_log
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

print("Tentando conectar ao Broker...")
client.connect(BROKER_ADDRESS, BROKER_PORT)

print("Loop de eventos iniciado...")
client.loop_forever()