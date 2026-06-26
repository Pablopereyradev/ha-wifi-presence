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
import json, os, re, subprocess, sys, time, unicodedata, urllib.request

OPTIONS_FILE = "/data/options.json"
MAC_RE = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")

def slugify(name):
    """Convierte un nombre en un id valido para entidad: 'iPhone de Pablo' -> 'iphone_de_pablo'."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "persona"

def detect_interface():
    """Autodetecta la interfaz con la ruta por defecto (la que da a la LAN)."""
    try:
        out = subprocess.run(["ip", "route", "show", "default"],
                             capture_output=True, text=True, timeout=5).stdout
        mm = re.search(r"\bdev\s+(\S+)", out)
        if mm:
            return mm.group(1)
    except Exception:
        pass
    return "eth0"

def load_config():
    """Carga la config del add-on (/data/options.json) o de variables de entorno (standalone)."""
    cfg = {}
    if os.path.exists(OPTIONS_FILE):
        with open(OPTIONS_FILE) as f:
            cfg = json.load(f)
    iface = cfg.get("interface") or os.getenv("IFACE", "")
    if not iface or iface.lower() == "auto":
        iface = detect_interface()
    scan_interval = int(cfg.get("scan_interval") or os.getenv("SCAN_INTERVAL", 30))
    away_timeout = int(cfg.get("away_timeout") or os.getenv("AWAY_TIMEOUT", 600))
    # personas: el usuario solo ingresa nombre + macs; el id (y la entidad) se derivan del nombre
    personas = {}
    for p in cfg.get("people", []):
        name = p.get("name") or p.get("id") or "persona"
        pid = slugify(name)
        personas[pid] = {
            "name": name,
            "macs": [m.lower() for m in p["macs"]],
            "away_timeout": int(p["away_timeout"]) if p.get("away_timeout") else away_timeout,
        }
    # Acceso a HA: dentro del add-on usa el Supervisor; standalone usa HA_URL/HA_TOKEN
    sup = os.getenv("SUPERVISOR_TOKEN")
    if sup:
        ha_url, ha_token = "http://supervisor/core", sup
    else:
        ha_url, ha_token = os.getenv("HA_URL", "http://homeassistant.local:8123"), os.getenv("HA_TOKEN", "")
    return iface, scan_interval, away_timeout, personas, ha_url, ha_token

IFACE, SCAN_INTERVAL, AWAY_TIMEOUT, PERSONAS, HA_URL, HA_TOKEN = load_config()
last_ip = {}

# Datos del broker MQTT (los pasa run.sh desde bashio::services); si no están,
# se usa el fallback por la API de Home Assistant (modo standalone).
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = os.getenv("MQTT_PORT", "1883")
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")

def _core_api_publish(topic, payload, retain):
    body = json.dumps({"topic": topic, "payload": payload, "retain": retain, "qos": 0}).encode()
    req = urllib.request.Request(HA_URL + "/api/services/mqtt/publish", data=body,
        headers={"Authorization": "Bearer " + HA_TOKEN, "Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=10)

def mqtt_publish(topic, payload, retain=True):
    """Publica al broker directo con mosquitto_pub; si no hay broker, usa la API de core."""
    if MQTT_HOST:
        cmd = ["mosquitto_pub", "-h", MQTT_HOST, "-p", str(MQTT_PORT), "-t", topic, "-m", payload]
        if retain:
            cmd.append("-r")
        if MQTT_USER:
            cmd += ["-u", MQTT_USER, "-P", MQTT_PASS]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return
            print("[mqtt] mosquitto_pub rc=%s %s" % (r.returncode, r.stderr.strip()), flush=True)
        except Exception as e:
            print("[mqtt] mosquitto_pub error:", e, flush=True)
    if HA_TOKEN:
        try:
            _core_api_publish(topic, payload, retain)
        except Exception as e:
            print("[mqtt] core api error:", e, flush=True)

def publish_discovery():
    for pid, p in PERSONAS.items():
        cfg = {
            "name": p["name"] + " WiFi",
            "unique_id": "wifi_presence_" + pid,
            "state_topic": "wifi_presence/" + pid + "/state",
            "json_attributes_topic": "wifi_presence/" + pid + "/attrs",
            "payload_home": "home", "payload_not_home": "away",
            "source_type": "router",
            "device": {"identifiers": ["wifi_presence_scanner"],
                       "name": "WiFi Presence", "model": "arp-scan", "manufacturer": "community"},
        }
        mqtt_publish("homeassistant/device_tracker/wifi_presence_" + pid + "/config", json.dumps(cfg))
    print("[init] discovery publicado para:", list(PERSONAS.keys()), flush=True)

def arp_scan_raw():
    """Escaneo arp a toda la subred. Devuelve lista de (ip, mac, fabricante)."""
    rows = []
    try:
        out = subprocess.run(["arp-scan", "--localnet", "--interface=" + IFACE, "--retry=3", "--timeout=300"],
                             capture_output=True, text=True, timeout=40).stdout
        for line in out.splitlines():
            mm = re.match(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})\s*(.*)", line)
            if mm:
                rows.append((mm.group(1), mm.group(2).lower(), (mm.group(3).strip() or "?")))
    except Exception as e:
        print("[scan] arp-scan error:", e, flush=True)
    return rows

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

def check_person(macs, found, neigh):
    """Determina si alguna MAC esta presente usando los resultados ya escaneados.
    Devuelve (present:bool, method:str|None)."""
    for m in macs:
        if m in found:
            last_ip[m] = found[m]
            return True, "arp-scan"
    ips = set()
    for m in macs:
        for ip in (neigh.get(m), last_ip.get(m)):
            if ip:
                ips.add(ip); last_ip[m] = ip
    for ip in ips:
        if arping_check(ip, macs):
            return True, "arping"
    return False, None

def log_discovery(rows):
    """Lista en el log todos los dispositivos de la red, marcando los configurados.
    Sirve para descubrir la MAC del telefono sin hurgar en los ajustes del iOS."""
    configured = {m for p in PERSONAS.values() for m in p["macs"]}
    print("[discover] === dispositivos detectados en la red (%s) ===" % IFACE, flush=True)
    if not rows:
        print("[discover] (ninguno; revisa la interfaz o permisos de red)", flush=True)
    for ip, mac, vendor in sorted(rows, key=lambda r: tuple(int(x) for x in r[0].split("."))):
        tag = "  <-- CONFIGURADO" if mac in configured else ""
        print("[discover]   %-15s  %s  %s%s" % (ip, mac, vendor, tag), flush=True)
    print("[discover] === copia la MAC de tu telefono y ponela en la config ===", flush=True)

def main():
    if not PERSONAS:
        print("[error] no hay personas configuradas. Revisa la configuracion.", flush=True)
        sys.exit(1)
    if not MQTT_HOST and not HA_TOKEN:
        print("[error] sin broker MQTT ni token de HA. Instalá/configurá MQTT.", flush=True)
        sys.exit(1)
    print("[init] WiFi Presence iniciado | interfaz=%s | intervalo=%ss | away=%ss" % (IFACE, SCAN_INTERVAL, AWAY_TIMEOUT), flush=True)
    publish_discovery()
    last_seen = {pid: 0.0 for pid in PERSONAS}
    last_state = {pid: None for pid in PERSONAS}
    first = True
    while True:
        now = time.time()
        # Un solo escaneo por ciclo, compartido por todas las personas:
        rows = arp_scan_raw()
        found = {mac: ip for ip, mac, _ in rows}
        neigh = kernel_neigh()
        if first:
            log_discovery(rows)   # descubrimiento de MAC al arrancar
            first = False
        for pid, p in PERSONAS.items():
            present, method = check_person(p["macs"], found, neigh)
            if present:
                last_seen[pid] = now
            timeout = p["away_timeout"]
            state = "home" if (now - last_seen[pid]) < timeout else "away"
            mqtt_publish("wifi_presence/" + pid + "/state", state)
            attrs = {
                "last_seen": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(last_seen[pid])) if last_seen[pid] else None,
                "seconds_since_seen": int(now - last_seen[pid]) if last_seen[pid] else None,
                "detection_method": method,
                "away_timeout": timeout,
            }
            mqtt_publish("wifi_presence/" + pid + "/attrs", json.dumps(attrs))
            if state != last_state[pid]:
                via = (" via %s" % method) if method else ""
                print(time.strftime("%H:%M:%S"), p["name"], "->", state, via, flush=True)
                last_state[pid] = state
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
