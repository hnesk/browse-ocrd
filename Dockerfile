FROM python:3.7

COPY Makefile /Makefile
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-dev make \
    && make -f /Makefile deps-ubuntu \
    && pip3 install -U setuptools --use-feature=2020-resolver \
    && pip3 install browse-ocrd --use-feature=2020-resolver \
    && rm /Makefile

MAINTAINER https://github.com/hnesk/browse-ocrd/issues

ENV GDK_BACKEND broadway
ENV BROADWAY_DISPLAY :5

EXPOSE 8085
EXPOSE 8080

VOLUME /data

COPY init.sh /init.sh
COPY serve.py /serve.py

WORKDIR /
CMD ["/init.sh", "/data"]
