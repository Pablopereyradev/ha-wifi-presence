#!/usr/bin/with-contenv bashio
# Arranque del add-on WiFi Presence.
# SUPERVISOR_TOKEN ya viene en el entorno; el script lee /data/options.json.

bashio::log.info "Iniciando WiFi Presence..."

# Aviso si MQTT no está disponible (el script publica por la API de HA, que necesita MQTT configurado)
if ! bashio::services.available "mqtt"; then
  bashio::log.warning "No se detectó el broker MQTT. Instalá y configurá Mosquitto + la integración MQTT en HA."
fi

exec python3 /presence_scanner.py
