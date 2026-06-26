# 📡 WiFi Presence — Add-on para Home Assistant

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
