FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IMAGEMAGICK_BINARY=/usr/bin/convert

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    gcc \
    ca-certificates \
    ffmpeg \
    fontconfig \
    imagemagick \
    libbz2-1.0 \
    libc6  \
    libcairo2-dev \
    libcom-err2 \
    libcrypt1 \
    libdb5.3 \
    libexpat1 \
    libffi8 \
    libgdbm6 \
    libgssapi-krb5-2 \
    libjpeg-dev \
    libk5crypto3 \
    libkeyutils1 \
    libkrb5-3 \
    libkrb5support0 \
    liblzma5 \
    libncursesw6 \
    libnsl2 \
    libpango1.0-dev \
    libreadline8 \
    libsqlite3-0 \
    libssl3 \
    libtinfo6 \
    libtirpc3 \
    libuuid1 \
    make \
    netbase \
    tzdata \
    vim \
    zlib1g \
    zlib1g-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir virtualenv
RUN python -m virtualenv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY ./requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 --upgrade pip && \
    pip install --no-cache-dir --default-timeout=300 -i https://pypi.org/simple -r requirements.txt

COPY . .

COPY ./policy.xml /etc/ImageMagick-6/policy.xml
RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<!--<policy domain="path" rights="none" pattern="@\*"-->/' /etc/ImageMagick-6/policy.xml || true

CMD ["bash", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
