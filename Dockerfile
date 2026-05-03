# Build stage — compile C extensions for armv7
ARG BUILD_FROM=ghcr.io/home-assistant/armv7-base-python:3.12
FROM ${BUILD_FROM} AS builder

# Install build dependencies for C extensions (cryptography needs gcc + libffi)
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

# Final stage — lean runtime image
FROM ${BUILD_FROM}

# Copy compiled packages from builder
COPY --from=builder /install /usr/local

# Copy integration
COPY custom_components/ /config/custom_components/

WORKDIR /config
