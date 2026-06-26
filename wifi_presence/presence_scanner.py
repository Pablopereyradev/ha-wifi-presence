#!/usr/bin/env python3
"""
WiFi Presence — detector de presencia por WiFi para Home Assistant.

Escanea la red local buscando las MAC de los dispositivos configurados y publica
un device_tracker por persona vía MQTT discovery. Combina 3 metodos de deteccion
para tolerar el sueno WiFi de los telefonos:
  1. arp-scan amplio a toda la subred
  2. lectura de la tabla ARP del kernel (ip neigh)
  3. arping dirigido a las IPs conocidas (verifica la MAC, evita falsos por DHCP)

Pensado para correr como add-on de Home Assistant OS: lee la configuracion de
/data/options.json y publica usando la API del Supervisor (sin token manual).
Tambien funciona standalone: ver variables de entorno HA_URL / HA_TOKEN.
"""
import json, os, re, subprocess, sys, time, urllib.request

OPTIONS_FILE = "/data/options.json"

def load_config():
    """Carga la config del add-on (/data/options.json) o de variables de entorno (standalone)."""
    cfg = {}
    if os.path.exists(OPTIONS_FILE):
        with open(OPTIONS_FILE) as f:
            cfg = json.load(f)
    iface = cfg.get("interface") or os.getenv("IFACE", "eth0")
    scan_interval = int(cfg.get("scan_interval") or os.getenv("SCAN_INTERVAL", 30))
    away_timeout = int(cfg.get("away_timeout") or os.getenv("AWAY_TIMEOUT", 600))
    # personas: lista de {id, name, macs:[...]}
    personas = {}
    for p in cfg.get("people", []):
        pid = p["id"].lower()
        personas[pid] = {"name": p.get("name", pid), "macs": [m.lower() for m in p["macs"]]}
    # Acceso a HA: dentro del add-on usa el Supervisor; standalone usa HA_URL/HA_TOKEN
    sup = os.getenv("SUPERVISOR_TOKEN")
    if sup:
        ha_url, ha_token = "http://supervisor/core", sup
    else:
        ha_url, ha_token = os.getenv("HA_URL", "http://homeassistant.local:8123"), os.getenv("HA_TOKEN", "")
    return iface, scan_interval, away_timeout, personas, ha_url, ha_token

IFACE, SCAN_INTERVAL, AWAY_TIMEOUT, PERSONAS, HA_URL, HA_TOKEN = load_config()
last_ip = {}

def ha_mqtt_publish(topic, payload, retain=True):
    body = json.dumps({"topic": topic, "payload": payload, "retain": retain, "qos": 0}).encode()
    req = urllib.request.Request(HA_URL + "/api/services/mqtt/publish", data=body,
        headers={"Authorization": "Bearer " + HA_TOKEN, "Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("[mqtt] publish error:", e, flush=True)

def publish_discovery():
    for pid, p in PERSONAS.items():
        cfg = {
            "name": p["name"] + " WiFi",
            "unique_id": "wifi_presence_" + pid,
            "state_topic": "wifi_presence/" + pid + "/state",
            "payload_home": "home", "payload_not_home": "away",
            "source_type": "router",
            "device": {"identifiers": ["wifi_presence_scanner"],
                       "name": "WiFi Presence", "model": "arp-scan", "manufacturer": "community"},
        }
        ha_mqtt_publish("homeassistant/device_tracker/wifi_presence_" + pid + "/config", json.dumps(cfg))
    print("[init] discovery publicado para:", list(PERSONAS.keys()), flush=True)

def arp_scan():
    found = {}
    try:
        out = subprocess.run(["arp-scan", "--localnet", "--interface=" + IFACE, "--retry=3", "--timeout=300"],
                             capture_output=True, text=True, timeout=40).stdout
        for line in out.splitlines():
            mm = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", line)
            if mm:
                found[mm.group(2).lower()] = mm.group(1)
    except Exception as e:
        print("[scan] arp-scan error:", e, flush=True)
    return found

def kernel_neigh():
    found = {}
    try:
        out = subprocess.run(["ip", "neigh"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            mm = re.search(r"(\d+\.\d+\.\d+\.\d+).*lladdr\s+([0-9a-fA-F:]{17})", line)
            if mm:
                found[mm.group(2).lower()] = mm.group(1)
    except Exception:
        pass
    return found

def arping_check(ip, macs):
    """ARP dirigido; True solo si responde con una MAC esperada (evita falsos por DHCP)."""
    try:
        r = subprocess.run(["arping", "-c", "5", "-w", "4", "-I", IFACE, ip],
                          capture_output=True, text=True, timeout=9)
        low = r.stdout.lower()
        return any(m in low for m in macs)
    except Exception:
        return False

def is_present(macs):
    found = arp_scan()
    for m in macs:
        if m in found:
            last_ip[m] = found[m]
            return True
    neigh = kernel_neigh()
    ips = set()
    for m in macs:
        for ip in (neigh.get(m), last_ip.get(m)):
            if ip:
                ips.add(ip); last_ip[m] = ip
    for ip in ips:
        if arping_check(ip, macs):
            return True
    return False

def main():
    if not PERSONAS:
        print("[error] no hay personas configuradas. Revisa la configuracion.", flush=True)
        sys.exit(1)
    if not HA_TOKEN:
        print("[error] sin token de HA (SUPERVISOR_TOKEN o HA_TOKEN).", flush=True)
        sys.exit(1)
    print("[init] WiFi Presence iniciado | interfaz=%s | intervalo=%ss | away=%ss" % (IFACE, SCAN_INTERVAL, AWAY_TIMEOUT), flush=True)
    publish_discovery()
    last_seen = {pid: 0.0 for pid in PERSONAS}
    last_state = {pid: None for pid in PERSONAS}
    while True:
        now = time.time()
        for pid, p in PERSONAS.items():
            if is_present(p["macs"]):
                last_seen[pid] = now
            state = "home" if (now - last_seen[pid]) < AWAY_TIMEOUT else "away"
            ha_mqtt_publish("wifi_presence/" + pid + "/state", state)
            if state != last_state[pid]:
                print(time.strftime("%H:%M:%S"), p["name"], "->", state, flush=True)
                last_state[pid] = state
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
