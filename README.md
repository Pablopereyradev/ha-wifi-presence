# 📡 WiFi Presence — Add-on para Home Assistant

**🇪🇸 Español** · [🇬🇧 English](#-wifi-presence--home-assistant-add-on)

Detección de presencia **por WiFi** para Home Assistant: sabe si una persona está en casa según si su **teléfono está conectado a la red**, sin depender del GPS ni de apps en el teléfono. Ideal para reemplazar `nmap_tracker` cuando da falsos "ausente".

Publica un `device_tracker` por persona (vía MQTT) que podés usar en automatizaciones o vincular a una `person`.

## ✨ Por qué este add-on

Los métodos clásicos (ping / `nmap_tracker`) fallan porque los teléfonos **duermen el WiFi** y dejan de responder. Este add-on combina **tres técnicas** para detectarlos de forma confiable:

1. **arp-scan** amplio a la subred
2. **Tabla ARP del kernel** (`ip neigh`)
3. **arping dirigido** a la IP del teléfono, verificando la MAC

Más una **histéresis** configurable que absorbe los silencios temporales del WiFi.

## 📦 Instalación

1. En Home Assistant: **Configuración → Add-ons → Add-on Store**
2. Menú (⋮ arriba a la derecha) → **Repositorios**
3. Pegá la URL de este repo:
   ```
   https://github.com/Pablopereyradev/ha-wifi-presence
   ```
4. Buscá **"WiFi Presence"** en la tienda e instalalo
5. En la pestaña **Configuración** del add-on, cargá tus personas y MAC (ver [DOCS](wifi_presence/DOCS.md))
6. Iniciá el add-on

> **Requisito:** tener el add-on **Mosquitto broker** + la integración **MQTT** configurados en HA.

## ⚙️ Configuración mínima

Al instalar, la pestaña **Configuración** muestra un **formulario**: agregás cada persona con su **nombre** y sus **MACs** (botón **+**). Equivalente en YAML:

```yaml
scan_interval: 30
away_timeout: 600
interface: end0
people:
  - name: iPhone de Persona 1   # define la entidad: device_tracker.iphone_de_persona_1_wifi
    macs:
      - "02:00:00:00:00:01"
```

La documentación completa (cómo sacar la MAC del teléfono, requisitos, limitaciones) está en **[wifi_presence/DOCS.md](wifi_presence/DOCS.md)**.

## ⚠️ Importante

- En iOS, poné la **"Dirección Wi-Fi privada" en "Fija"** para esa red (si rota, el add-on pierde el teléfono).
- Es detección **a nivel casa** (no por habitación) y es un método **activo**: en sueño muy profundo (madrugada) un teléfono puede dar un falso "fuera"; subí `away_timeout` para mitigarlo.

## 📝 Licencia

MIT — ver [LICENSE](LICENSE).

---

# 📡 WiFi Presence — Home Assistant Add-on

[🇪🇸 Español](#-wifi-presence--add-on-para-home-assistant) · **🇬🇧 English**

**WiFi-based presence detection** for Home Assistant: it knows whether a person is home based on whether their **phone is connected to the network**, without relying on GPS or phone apps. A great replacement for `nmap_tracker` when it reports false "away".

It publishes one `device_tracker` per person (over MQTT) that you can use in automations or link to a `person`.

## ✨ Why this add-on

Classic methods (ping / `nmap_tracker`) fail because phones **sleep their WiFi** and stop responding. This add-on combines **three techniques** for reliable detection:

1. Broad **arp-scan** of the subnet
2. **Kernel ARP table** (`ip neigh`)
3. **Targeted arping** to the phone's IP, verifying the MAC

Plus a configurable **hysteresis** that absorbs temporary WiFi silences.

## 📦 Installation

1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Menu (⋮ top right) → **Repositories**
3. Paste this repo's URL:
   ```
   https://github.com/Pablopereyradev/ha-wifi-presence
   ```
4. Find **"WiFi Presence"** in the store and install it
5. In the add-on's **Configuration** tab, add your people and MACs
6. Start the add-on

> **Requirement:** the **Mosquitto broker** add-on + the **MQTT** integration configured in HA.

## ⚙️ Minimal configuration

On install, the **Configuration** tab shows a **form**: add each person with their **name** and **MACs** (**+** button). YAML equivalent:

```yaml
scan_interval: 30
away_timeout: 600
interface: auto       # auto-detects the LAN interface
people:
  - name: Pablo's iPhone   # defines the entity: device_tracker.pablo_s_iphone_wifi
    macs:
      - "02:00:00:00:00:01"
```

> 💡 **Finding the MAC is easy:** on first start the add-on **lists every device on your network** (IP + MAC + vendor) in its log, marking the configured ones. Just read the log, find your phone, and copy its MAC.

## ⚠️ Notes

- On iOS, set the **"Private Wi-Fi Address" to "Fixed"** for that network (if it rotates, the add-on loses the phone).
- Detection is **house-level** (not per-room) and **active** (it probes): in very deep sleep (overnight) a phone may report a false "away"; raise `away_timeout` to mitigate.

## 📝 License

MIT — see [LICENSE](LICENSE).
