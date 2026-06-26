#!/usr/bin/with-contenv bashio
# Arranque del add-on WiFi Presence.
# SUPERVISOR_TOKEN ya viene en el entorno; el script lee /data/options.json.

bashio::log.info "Iniciando WiFi Presence..."

# Si el broker MQTT está disponible, pasamos sus credenciales al script para
# publicar directo (más confiable que el proxy de la API de core).
if bashio::services.available "mqtt"; then
  export MQTT_HOST="$(bashio::services mqtt 'host')"
  export MQTT_PORT="$(bashio::services mqtt 'port')"
  export MQTT_USER="$(bashio::services mqtt 'username')"
  export MQTT_PASS="$(bashio::services mqtt 'password')"
  bashio::log.info "Broker MQTT detectado en ${MQTT_HOST}:${MQTT_PORT}"
else
  bashio::log.warning "No se detectó el broker MQTT. Instalá y configurá Mosquitto + la integración MQTT en HA."
fi

exec python3 /presence_scanner.py
