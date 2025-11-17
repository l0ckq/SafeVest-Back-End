import paho.mqtt.client as mqtt
import time
import json
import random
from datetime import datetime

# --------------------
# CONFIGURAÇÕES
# --------------------
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh"
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "vest"

# Vestes simuladas (devem estar cadastradas no Django!)
VESTES_EM_OPERACAO = [
    "SV-DEMO-01",
    "SV-DEMO-02",
    "SV-DEMO-03",
]

INTERVALO_ENVIO = 5  # segundos entre cada envio

# --------------------
# LOGS
# --------------------
def log(msg, nivel="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    cores = {"INFO": "\033[94m", "OK": "\033[92m", "WARN": "\033[93m", "ERROR": "\033[91m"}
    reset = "\033[0m"
    print(f"{cores.get(nivel, '')}{timestamp} {msg}{reset}")

# --------------------
# CALLBACKS MQTT
# --------------------
conectado = False
mensagens_enviadas = 0

def on_connect(client, userdata, flags, rc, properties=None):
    global conectado
    if rc == 0:
        conectado = True
        log("✓ Conectado ao broker MQTT!", "OK")
        log(f"🎯 Publicando no tópico: '{MQTT_TOPIC}'", "OK")
    else:
        log(f"❌ Falha ao conectar (código {rc})", "ERROR")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    global mensagens_enviadas
    mensagens_enviadas += 1

def on_disconnect(client, userdata, flags, rc, properties=None):
    global conectado
    conectado = False
    if rc != 0:
        log(f"⚠️  Desconectado inesperadamente (rc={rc})", "WARN")

# --------------------
# GERAÇÃO DE DADOS
# --------------------
def gerar_dados_normais():
    """Gera dados de sinais vitais normais"""
    return {
        "bpm": random.randint(70, 110),
        "temp": round(random.uniform(36.1, 37.2), 2),
        "humi": round(random.uniform(40.0, 60.0), 2),
        "mq2": round(random.uniform(0.5, 1.5), 2)
    }

def gerar_dados_anormais():
    """Gera dados que devem disparar alertas"""
    tipo = random.choice(["alerta", "emergencia"])
    
    if tipo == "alerta":
        # BPM entre 121-160 ou 50-59 (Alerta)
        bpm = random.choice([
            random.randint(121, 160),
            random.randint(50, 59)
        ])
        temp = round(random.uniform(37.3, 37.9), 2)
    else:
        # BPM > 160 ou < 50 (Emergência)
        bpm = random.choice([
            random.randint(161, 180),
            random.randint(40, 49)
        ])
        temp = round(random.uniform(38.0, 39.5), 2)
    
    return {
        "bpm": bpm,
        "temp": temp,
        "humi": round(random.uniform(30.0, 70.0), 2),
        "mq2": round(random.uniform(1.6, 3.0), 2)
    }

# --------------------
# MAIN
# --------------------
def main():
    print("\n" + "="*60)
    log("🔬 Simulador de Sensores SafeVest")
    print("="*60 + "\n")
    
    log(f"Vestes em operação: {', '.join(VESTES_EM_OPERACAO)}")
    log(f"Intervalo de envio: {INTERVALO_ENVIO}s")
    log(f"Broker: {BROKER_ADDRESS}:{BROKER_PORT}")
    log(f"Tópico: {MQTT_TOPIC}\n")
    
    # Cria cliente MQTT
    client = mqtt.Client(
        client_id="sensor_simulador_safevest",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    
    # Conecta ao broker
    log("Conectando ao broker...")
    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT)
        client.loop_start()
    except Exception as e:
        log(f"❌ Erro ao conectar: {e}", "ERROR")
        return
    
    # Aguarda conexão
    tentativas = 0
    while not conectado and tentativas < 10:
        time.sleep(0.5)
        tentativas += 1
    
    if not conectado:
        log("❌ Não foi possível conectar após 5s", "ERROR")
        return
    
    print("="*60)
    log("✓ Sistema operacional! Iniciando envio de dados...", "OK")
    log("⚠️  ATENÇÃO: Certifique-se que estas vestes estão cadastradas no Django!", "WARN")
    print("="*60 + "\n")
    
    # Loop principal
    try:
        ciclo = 0
        while True:
            ciclo += 1
            serial_selecionado = random.choice(VESTES_EM_OPERACAO)
            
            # 15% de chance de gerar dados anormais
            if random.random() < 0.15:
                dados = gerar_dados_anormais()
                status_emoji = "🚨"
                status_texto = "ANORMAL"
            else:
                dados = gerar_dados_normais()
                status_emoji = "💚"
                status_texto = "NORMAL"
            
            # Monta payload
            payload = {
                "device_id": serial_selecionado,
                "bpm": dados["bpm"],
                "temp": dados["temp"],
                "humi": dados["humi"],
                "mq2": dados["mq2"]
            }
            
            payload_json = json.dumps(payload)
            
            # Publica no broker
            result = client.publish(MQTT_TOPIC, payload_json)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                log(f"{status_emoji} Ciclo #{ciclo} | {serial_selecionado} | {status_texto}")
                log(f"   📊 BPM: {dados['bpm']} | TEMP: {dados['temp']}°C | HUMI: {dados['humi']}% | MQ2: {dados['mq2']}")
                log(f"   ✓ Publicado ({mensagens_enviadas} msgs enviadas)\n")
            else:
                log(f"❌ Falha ao publicar (rc={result.rc})", "ERROR")
            
            time.sleep(INTERVALO_ENVIO)
            
    except KeyboardInterrupt:
        print("\n" + "="*60)
        log("👋 Simulador encerrado pelo usuário")
        log(f"📊 Total de mensagens enviadas: {mensagens_enviadas}", "OK")
        print("="*60)
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()