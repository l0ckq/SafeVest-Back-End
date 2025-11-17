#!/usr/bin/env python3
# cerebro-service.py
import json
import time
import requests
import paho.mqtt.client as mqtt
from threading import Thread, Event

# --------------------
# CONFIGURAÇÕES
# --------------------
API_BASE = "http://127.0.0.1:8000/api"
API_LOGIN = f"{API_BASE}/token/"
API_REFRESH = f"{API_BASE}/token/refresh/"
API_MAPA_VESTES = f"{API_BASE}/vestes/mapa/"
API_LEITURAS = f"{API_BASE}/leiturasensor/"
API_ALERTAS = f"{API_BASE}/alertas/"

# credenciais do serviço (ajuste se necessário)
SERVICE_USER = "admin@safevest.com"
SERVICE_PASS = "admin"

BROKER = "jaragua-01.lmq.cloudamqp.com"
PORT = 1883
MQTT_USER = "qyyguyzh:qyyguyzh"
MQTT_PASS = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
TOPIC = "vest"

# tokens
access_token = None
refresh_token = None

# sinal pra encerrar threads
stop_event = Event()

# --------------------
# LOGS simples
# --------------------
def log(tag, msg):
    print(f"[{tag}] {msg}")

def log_error(tag, msg):
    print(f"[{tag} ERROR] {msg}")

# --------------------
# HELPERS HTTP
# --------------------
JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

def try_post(url, payload, headers=None, timeout=8):
    """Faz POST com tratamento de exceção e retorna (resp or None)."""
    try:
        r = requests.post(url, json=payload, headers=headers or JSON_HEADERS, timeout=timeout)
        return r
    except Exception as e:
        log_error("HTTP", f"POST {url} falhou: {e}")
        return None

def try_get(url, headers=None, timeout=8):
    try:
        r = requests.get(url, headers=headers or JSON_HEADERS, timeout=timeout)
        return r
    except Exception as e:
        log_error("HTTP", f"GET {url} falhou: {e}")
        return None

# --------------------
# AUTENTICAÇÃO (robusta)
# --------------------
def autenticar_tentativas():
    """
    Tenta autenticar com os formatos possíveis:
      1) {"email":..., "password":...}
      2) {"username":..., "password":...}
    Retorna True se ok e salva access_token/refresh_token.
    """
    global access_token, refresh_token

    log("AUTH", "Tentando autenticar (formato email)...")
    payload_email = {"email": SERVICE_USER, "password": SERVICE_PASS}
    resp = try_post(API_LOGIN, payload_email)

    if resp is None:
        log_error("AUTH", "Nenhuma resposta do servidor.")
        return False

    # Se retornou 400 contendo 'username' significa que endpoint recebeu mas espera username
    if resp.ok:
        data = resp.json()
        access_token = data.get("access")
        refresh_token = data.get("refresh")
        log("AUTH", "Autenticado com sucesso (email).")
        return True

    # log da resposta para debugar
    log_error("AUTH", f"Falha (email). status={resp.status_code} body={resp.text}")

    # tenta com username se o primeiro falhou
    log("AUTH", "Tentando autenticar (formato username)...")
    payload_username = {"username": SERVICE_USER, "password": SERVICE_PASS}
    resp2 = try_post(API_LOGIN, payload_username)

    if resp2 is None:
        log_error("AUTH", "Nenhuma resposta do servidor (username).")
        return False

    if resp2.ok:
        data = resp2.json()
        access_token = data.get("access")
        refresh_token = data.get("refresh")
        log("AUTH", "Autenticado com sucesso (username).")
        return True

    log_error("AUTH", f"Falha (username). status={resp2.status_code} body={resp2.text}")

    # última tentativa: tentar enviar AMBOS os campos (algumas views aceitam)
    log("AUTH", "Tentando autenticar (formato combinado email+username)...")
    payload_both = {"email": SERVICE_USER, "username": SERVICE_USER, "password": SERVICE_PASS}
    resp3 = try_post(API_LOGIN, payload_both)

    if resp3 and resp3.ok:
        data = resp3.json()
        access_token = data.get("access")
        refresh_token = data.get("refresh")
        log("AUTH", "Autenticado com sucesso (combinado).")
        return True

    if resp3:
        log_error("AUTH", f"Falha (combinado). status={resp3.status_code} body={resp3.text}")

    return False

def refresh_tokens():
    """Atualiza token usando refresh_token; se falhar tenta re-autenticar."""
    global access_token, refresh_token
    if not refresh_token:
        log_error("AUTH", "Nenhum refresh_token disponível.")
        return autenticar_tentativas()

    log("AUTH", "Solicitando refresh de token...")
    resp = try_post(API_REFRESH, {"refresh": refresh_token})
    if resp is None:
        return False

    if resp.ok:
        access_token = resp.json().get("access")
        log("AUTH", "Refresh OK.")
        return True

    log_error("AUTH", f"Refresh falhou: status={resp.status_code} body={resp.text}")
    return autenticar_tentativas()

def get_headers():
    global access_token
    if not access_token:
        log("AUTH", "Sem access_token, autenticando...")
        if not autenticar_tentativas():
            return None
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "Accept": "application/json"}

# --------------------
# CACHE DE VESTES (thread)
# --------------------
vestes_cache = {}

def atualizar_cache_loop(poll_seconds=60):
    """Loop que atualiza o mapa das vestes via API."""
    global vestes_cache
    while not stop_event.is_set():
        log("CACHE", "Atualizando mapa das vestes...")
        headers = get_headers()
        if headers is None:
            log_error("CACHE", "Não foi possível obter headers (auth). Aguardando 5s...")
            time.sleep(5)
            continue

        resp = try_get(API_MAPA_VESTES, headers=headers)
        if resp is None:
            time.sleep(poll_seconds)
            continue

        if resp.status_code == 401:
            log_error("CACHE", "401 ao buscar mapa (token inválido). Tentando refresh.")
            if refresh_tokens():
                headers = get_headers()
                resp = try_get(API_MAPA_VESTES, headers=headers)
            else:
                time.sleep(5)
                continue

        if resp.ok:
            try:
                novas = {}
                for v in resp.json():
                    # padroniza: numero_de_serie -> {id, usuario}
                    key = v.get("numero_de_serie") or v.get("numero_de_serie", "")
                    novas[key] = {"id": v.get("id"), "usuario": v.get("usuario")}
                vestes_cache = novas
                log("CACHE", f"Mapa atualizado ({len(vestes_cache)} vestes).")
            except Exception as e:
                log_error("CACHE", f"Erro ao montar cache: {e} body={resp.text}")
        else:
            log_error("CACHE", f"Erro resposta: {resp.status_code} body={resp.text}")

        time.sleep(poll_seconds)

# --------------------
# LÓGICA DE PROCESSAMENTO MQTT
# --------------------
def calcular_status(bpm):
    if bpm is None:
        return "Indefinido"
    try:
        bpm = int(bpm)
    except Exception:
        return "Indefinido"
    if bpm > 160 or bpm < 50:
        return "Emergência"
    if bpm > 120 or bpm < 60:
        return "Alerta"
    return "Seguro"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log("MQTT", f"Conectado ao broker (rc={rc}). Inscrevendo em '{TOPIC}'")
        client.subscribe(TOPIC)
    else:
        log_error("MQTT", f"Falha ao conectar (rc={rc}).")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        log_error("MQTT", f"Payload inválido: {e}")
        return

    log("MQTT", f"Recebido: {payload}")

    serial = payload.get("device_id") or payload.get("numero_de_serie") or payload.get("serial")
    if not serial:
        log_error("MQTT", "Mensagem sem device_id/numero_de_serie/serial.")
        return

    if serial not in vestes_cache:
        log_error("MQTT", f"Serial '{serial}' não encontrada no cache.")
        return

    meta = vestes_cache[serial]
    id_veste = meta.get("id")
    id_usuario = meta.get("usuario")

    leitura_payload = {
        "veste": id_veste,
        "bpm": payload.get("bpm"),
        "temp": payload.get("temp"),
        "humi": payload.get("humi"),
        "mq2": payload.get("mq2")
    }

    headers = get_headers()
    if headers is None:
        log_error("MQTT", "Sem headers (auth) para enviar leitura.")
        return

    resp = try_post(API_LEITURAS, leitura_payload, headers=headers)
    if resp is None:
        return

    if resp.status_code == 401:
        log_error("MQTT", "401 ao salvar leitura. Tentar refresh e reenviar.")
        if refresh_tokens():
            headers = get_headers()
            resp = try_post(API_LEITURAS, leitura_payload, headers=headers)
        else:
            return

    if not resp.ok:
        log_error("MQTT", f"Falha ao salvar leitura: {resp.status_code} {resp.text}")
        return

    leitura_obj = resp.json()
    leitura_id = leitura_obj.get("id") or leitura_obj.get("pk")
    log("MQTT", f"Leitura salva (id={leitura_id})")

    status = calcular_status(payload.get("bpm"))
    log("MQTT", f"Status calculado: {status}")

    if status in ("Alerta", "Emergência"):
        if not id_usuario:
            log("MQTT", "Veste sem usuário — alerta ignorado.")
            return

        alerta_payload = {
            "profile": id_usuario,
            "leitura_associada": leitura_id,
            "tipo_alerta": status
        }
        resp_alert = try_post(API_ALERTAS, alerta_payload, headers=headers)
        if resp_alert is None:
            return
        if resp_alert.status_code == 401:
            log_error("ALERTA", "401 ao criar alerta — tentando refresh.")
            if refresh_tokens():
                headers = get_headers()
                resp_alert = try_post(API_ALERTAS, alerta_payload, headers=headers)
        if resp_alert.ok:
            log("ALERTA", f"Alerta '{status}' criado para profile {id_usuario}.")
        else:
            log_error("ALERTA", f"Falha ao criar alerta: {resp_alert.status_code} {resp_alert.text}")

# --------------------
# STARTUP
# --------------------
def main():
    log("SYSTEM", "Iniciando Cérebro SafeVest")

    ok = autenticar_tentativas()
    if not ok:
        log_error("AUTH", "Não foi possível autenticar em nenhum formato. Vou mostrar recomendações:")
        log("AUTH", "  - Verifique se EMAIL/SENHA SERVICE_USER estão corretos.")
        log("AUTH", "  - Verifique se /api/token/ está mapeado para EmailTokenObtainPairView.")
        log("AUTH", "  - Teste com curl/postman:")
        log("AUTH", f"    curl -X POST {API_LOGIN} -H 'Content-Type: application/json' -d '{{\"email\":\"{SERVICE_USER}\",\"password\":\"{SERVICE_PASS}\"}}'")
        return

    # iniciar thread de cache
    t = Thread(target=atualizar_cache_loop, daemon=True)
    t.start()

    client = mqtt.Client(
        client_id="cerebro_service",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    log("MQTT", f"Tentando conectar ao broker {BROKER}:{PORT} ...")
    try:
        client.connect(BROKER, PORT)
    except Exception as e:
        log_error("MQTT", f"Falha ao conectar ao broker: {e}")
        stop_event.set()
        return

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        log("SYSTEM", "Recebido KeyboardInterrupt; encerrando...")
        stop_event.set()
        client.disconnect()

if __name__ == "__main__":
    main()