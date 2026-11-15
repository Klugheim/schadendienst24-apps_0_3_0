ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-matplotlib \
    py3-reportlab \
    py3-requests \
    tzdata

WORKDIR /app

COPY run.sh /run.sh
COPY report.py /app/report.py


RUN chmod a+x /run.sh

CMD ["/run.sh"]
COPY zuordnung.py /app/zuordnung.py
