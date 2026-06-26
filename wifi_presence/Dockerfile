ARG BUILD_FROM
FROM ${BUILD_FROM}

# Dependencias: python3 + arp-scan + arping (iputils)
RUN apk add --no-cache python3 arp-scan iputils

# Script
COPY presence_scanner.py /presence_scanner.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
