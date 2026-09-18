FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Copy the application code
COPY k8s_ops/ ./k8s_ops/

# Create a non-root user
RUN useradd -m -u 1000 k8sops && \
    chown -R k8sops:k8sops /app
USER k8sops

# Set the default command
ENTRYPOINT ["k8s-ops"]
CMD ["--help"]
