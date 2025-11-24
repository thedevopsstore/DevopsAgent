# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files first
COPY pyproject.toml .

# Install dependencies using uv
# --system installs into the system python environment (no venv needed in container)
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Expose ports for A2A Server (9000) and Streamlit UI (8501)
EXPOSE 9000
EXPOSE 8501

# Create a startup script
RUN echo '#!/bin/bash\n\
python main.py & \n\
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0\n\
wait' > /app/start.sh && chmod +x /app/start.sh

# Set entrypoint
CMD ["/app/start.sh"]
