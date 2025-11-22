import paho.mqtt.client as mqtt
import json
import requests
import time
from requests.exceptions import RequestException

# =====================================================
# CONFIGURAÇÕES DO BROKER
# =====================================================
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh"
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/dados_sensores"

# =====================================================
# CONFIGURAÇÕES DA API SAFE-VEST
# =====================================================
API_BASE_URL = "http://127.0.0.1:8000/api"
API_LOGIN_URL = f"{API_BASE_URL}/token/"
API_REFRESH_URL = f"{API_BASE_URL}/token/refresh/"
API_VESTES_ENDPOINT = f"{API_BASE_URL}/vestes/buscar/"
API_LEITURAS_ENDPOINT = f"{API_BASE_URL}/leiturasensor/"
API_ALERTAS_ENDPOINT = f"{API_BASE_URL}/alertas/"

# Credenciais fixas para o serviço do cérebro (crie esse usuário no Django)
SERVICE_USER = "admin@safevest.com"
SERVICE_PASS = "admin"

# =====================================================
# AUTENTICAÇÃO AUTOMÁTICA
# =====================================================
access_token = None
refresh_token = None

def autenticar():
    """Faz login e obtém novo par de tokens JWT"""
    global access_token, refresh_token
    try:
        response = requests.post(API_LOGIN_URL, json={"username": SERVICE_USER, "password": SERVICE_PASS})
        if response.ok:
            tokens = response.json()
            access_token = tokens.get("access")
            refresh_token = tokens.get("refresh")
            print("[AUTH] Novo token obtido com sucesso.")
            return True
        else:
            print(f"[AUTH] Falha no login ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[AUTH] Erro ao autenticar: {e}")
        return False

def refresh():
    """Tenta atualizar o token de acesso usando o refresh_token"""
    global access_token, refresh_token
    if not refresh_token:
        print("[AUTH] Nenhum refresh_token disponível, refazendo login...")
        return autenticar()
    try:
        response = requests.post(API_REFRESH_URL, json={"refresh": refresh_token})
        if response.ok:
            data = response.json()
            access_token = data.get("access")
            print("[AUTH] Token atualizado com sucesso.")
            return True
        else:
            print(f"[AUTH] Refresh falhou ({response.status_code}), refazendo login...")
            return autenticar()
    except Exception as e:
        print(f"[AUTH] Erro ao tentar atualizar token: {e}")
        return autenticar()

def get_headers():
    """Monta headers sempre com token válido"""
    global access_token
    if not access_token:
        autenticar()
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

# =====================================================
# FUNÇÕES DE REQUISIÇÃO SEGURA
# =====================================================
def safe_post(url, payload, max_retries=2):
    for attempt in range(max_retries):
        try:
            headers = get_headers()
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 401:
                print("[AUTH] Token expirado, atualizando...")
                if refresh():
                    continue
            return resp
        except RequestException as e:
            print(f"[HTTP] Erro POST {url}: {e} (tentativa {attempt+1})")
            time.sleep(1)
    return None

def safe_get(url, max_retries=2):
    for attempt in range(max_retries):
        try:
            headers = get_headers()
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 401:
                print("[AUTH] Token expirado, atualizando...")
                if refresh():
                    continue
            return resp
        except RequestException as e:
            print(f"[HTTP] Erro GET {url}: {e} (tentativa {attempt+1})")
            time.sleep(1)
    return None

# =====================================================
# LÓGICA DO CÉREBRO
# =====================================================
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"--- CÉREBRO CONECTADO! Resultado: {mqtt.connack_string(rc)} ---")
    client.subscribe(MQTT_TOPIC)
    print(f"--- OUVINDO o tópico: {MQTT_TOPIC} ---")

def calcularStatus(data):
    bpm = data.get("bpm", 0)
    try:
        bpm = int(bpm)
    except:
        bpm = 0
    if bpm > 160 or bpm < 50:
        return "Emergência"
    if bpm > 120 or bpm < 60:
        return "Alerta"
    return "Seguro"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        print(f"<- Recebido: {data}")

        serial = data.get("device_id") or data.get("numero_de_serie")
        if not serial:
            print("   |-> ERRO: Payload sem 'device_id', 'numero_de_serie' ou 'serial'.")
            return

        # Consulta veste
        query_url = f"{API_VESTES_ENDPOINT}?numero_de_serie={serial}"
        resp_veste = safe_get(query_url)
        if not resp_veste or not resp_veste.ok:
            print(f"   |-> ERRO ao buscar veste {serial}: {getattr(resp_veste, 'status_code', '?')} {getattr(resp_veste, 'text', '')}")
            return

        data_veste = resp_veste.json()
        if not data_veste:
            print(f"   |-> ERRO: Nenhuma veste encontrada para {serial}")
            return

        veste = data_veste[0]
        id_veste = veste.get("id")
        id_usuario = veste.get("profile", {}).get("user", {}).get("id")
        
        if not id_usuario:
            print(f"   |-> AVISO: Veste {serial} sem usuário vinculado.")
            return
        print(f"   |-> Veste {id_veste} vinculada ao Usuário {id_usuario}")

        # Monta leitura conforme serializer
        leitura_payload = {
            "veste": id_veste,
            "batimento": data.get("batimento"),
            "temperatura_A": data.get("temperatura_A"),
            "temperatura_C": data.get("temperatura_C"),
            "nivel_co": data.get("nivel_co"),
            "nivel_bateria": data.get("nivel_bateria")
        }

        resp_leitura = safe_post(API_LEITURAS_ENDPOINT, leitura_payload)
        if not resp_leitura or not resp_leitura.ok:
            print(f"   |-> ERRO ao salvar leitura: {getattr(resp_leitura, 'status_code', '?')} {getattr(resp_leitura, 'text', '')}")
            return

        leitura_salva = resp_leitura.json()
        print(f"   |-> Leitura salva com sucesso: {leitura_salva}")

        status = calcularStatus(data)
        print(f"   |-> Status calculado: {status}")

        if status in ["Alerta", "Emergência"]:
            alerta_payload = {
                "leitura_associada": leitura_salva.get("id"),
                "tipo_alerta": status
            }
            resp_alerta = safe_post(API_ALERTAS_ENDPOINT, alerta_payload)
            if resp_alerta and resp_alerta.ok:
                print(f"   |-> ALERTA '{status}' registrado com sucesso!")
            else:
                print(f"   |-> ERRO ao criar alerta: {getattr(resp_alerta, 'status_code', '?')} {getattr(resp_alerta, 'text', '')}")

    except Exception as e:
        print(f"[ERRO GERAL] {e}")

# =====================================================
# MAIN
# =====================================================
print("Iniciando o Cérebro do SafeVest...")

autenticar()  # login inicial

client = mqtt.Client(client_id="cerebro_service_main")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

try:
    print("Tentando conectar ao Broker MQTT...")
    client.connect(BROKER_ADDRESS, BROKER_PORT)
    client.loop_forever()
except Exception as e:
    print(f"Falha ao conectar ao broker: {e}")