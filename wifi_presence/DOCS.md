# WiFi Presence — Documentación

Detecta si una persona está en casa según si su **teléfono está conectado al WiFi**, sin depender del GPS ni de apps en el teléfono. Publica un `device_tracker` por persona en Home Assistant.

## Cómo funciona

Cada `scan_interval` segundos, el add-on combina **tres métodos** para confirmar si el teléfono de cada persona está en la red:

1. **arp-scan amplio** — "pasa lista" a toda la subred preguntando quién responde.
2. **Tabla ARP del kernel** (`ip neigh`) — revisa qué dispositivos ya conoce el sistema.
3. **arping dirigido** — le insiste directamente a la última IP conocida del teléfono, verificando que responda con la **MAC esperada** (evita falsos positivos si el router reasignó esa IP a otro dispositivo).

Si **ninguna** de las MAC de la persona responde durante `away_timeout` segundos seguidos, se la marca **fuera** (`away`). Esta "histéresis" absorbe el sueño del WiFi de los teléfonos (que dejan de responder por ratos aunque estén en casa).

## Requisitos

- **Broker MQTT**: add-on *Mosquitto broker* instalado + integración **MQTT** configurada en HA. El add-on publica el `device_tracker` por MQTT discovery.
- **Red en la misma capa 2**: el add-on usa `host_network` y debe estar en la misma red/VLAN que los teléfonos.
- **MAC fija en los iPhones**: en iOS, entrá a *Ajustes → Wi-Fi → ⓘ de tu red → "Dirección Wi-Fi privada"* y ponela en **"Fija"** (o desactivada). Si está en "Rotativa", la MAC cambia y el add-on pierde el teléfono.

## Configuración

Al instalar el add-on, en la pestaña **Configuración** vas a ver un **formulario**: completás el intervalo, el timeout, la interfaz y la lista de **personas** (un botón **+** para agregar cada una con su **nombre** y sus **MACs**). No hace falta editar YAML a mano.

El equivalente en YAML (vista "Editar en YAML"):

```yaml
scan_interval: 30        # segundos entre escaneos (10–300)
away_timeout: 600        # segundos sin ver el teléfono para marcar "fuera" (60–3600)
interface: end0          # interfaz de red del host (ver abajo cómo averiguarla)
people:
  - name: iPhone de Persona 1   # el nombre define la entidad: device_tracker.iphone_de_persona_1_wifi
    macs:                       # una o varias MAC (ej. 2.4GHz y 5GHz)
      - "02:00:00:00:00:01"
  - name: iPhone de Persona 2
    macs:
      - "02:00:00:00:00:02"
      - "02:00:00:00:00:03"
```

> El **nombre** es lo único que define la entidad: el add-on lo convierte a minúsculas/guiones bajos. Ej.: `iPhone de Pablo` → `device_tracker.iphone_de_pablo_wifi`.

### Cómo averiguar la `interface`
En HAOS suele ser `end0`, `eth0` o `enp0s3`. Mirá en *Configuración → Sistema → Red*, o probá las comunes. Debe ser la interfaz conectada a tu LAN.

### Cómo obtener la MAC de cada teléfono
- **iPhone**: *Ajustes → Wi-Fi → ⓘ de tu red → "Dirección Wi-Fi"* (poné la privada en "Fija" primero). Si tenés bandas 2.4 y 5GHz separadas, puede haber una MAC por banda — agregá ambas.
- **Android**: *Ajustes → WiFi → tu red → Avanzado → Dirección MAC* (poné "MAC del dispositivo" / desactivá MAC aleatoria para esa red).

## Resultado en Home Assistant

Por cada persona se crea un `device_tracker.<name>_wifi` con estado `home` / `not_home`. Para usarlo como presencia "oficial":

*Configuración → Personas → (tu persona) → Dispositivos a seguir → agregá `device_tracker.<name>_wifi`.*

> 💡 Si lo usás como **única** fuente de la persona, evitás que un GPS "congelado" la deje en casa por error.

## Limitaciones (honestas)

- Detecta presencia **en la casa**, no en qué habitación.
- Es un método **activo** (sondea). Los teléfonos en **sueño profundo** (madrugada) pueden no responder por períodos largos y dar un falso "fuera". Subir `away_timeout` (ej. 1500 = 25 min) lo mitiga, a costa de tardar más en detectar la salida real.
- Necesita que la MAC del teléfono **no rote**.
