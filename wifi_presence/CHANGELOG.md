# Changelog

## 1.2.1

- **Instalación por descarga directa**: se usa la imagen pre-compilada de GHCR
  (`image:`), así Home Assistant ya no compila nada en el equipo al instalar.

## 1.2.0

- **Descubrimiento de MAC**: al arrancar, el add-on lista en el log todos los
  dispositivos de la red con su IP y fabricante, marcando los ya configurados.
  Ya no hace falta hurgar en los ajustes del teléfono para encontrar la MAC.
- **Autodetección de la interfaz de red**: dejá `interface: auto` y la detecta sola.
- **Eficiencia**: ahora se hace **un solo escaneo por ciclo** compartido entre todas
  las personas (antes era uno por persona).
- **Atributos `last_seen`**: cada `device_tracker` expone la última vez visto,
  los segundos desde entonces y el método de detección (arp-scan / arping).
- **`away_timeout` por persona** (opcional): override del timeout global.
- **Validación de MAC** en el formulario (rechaza formatos inválidos).

## 1.1.4

- Ícono y logo del add-on.

## 1.1.3

- Etiqueta del formulario: "Teléfonos / dispositivos".

## 1.1.2

- Fix de build: `BUILD_FROM` con valor por defecto + `build.yaml`.

## 1.1.0

- Configuración simplificada: solo Nombre + MACs; la entidad se deriva del nombre.

## 1.0.0

- Versión inicial: detección de presencia por WiFi (arp-scan + ARP del kernel +
  arping dirigido) con histéresis, publicando un `device_tracker` por persona vía MQTT.
