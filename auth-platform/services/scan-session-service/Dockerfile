FROM python:3.12-slim
WORKDIR /app

# Install service dependencies
COPY services/scan-session-service/pyproject.toml .
RUN python3 -c "import tomllib; deps=tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; open('requirements.txt','w').write('\n'.join(deps))" && \
    pip install --no-cache-dir -r requirements.txt

# Install shared library
COPY libs/auth_common /tmp/auth_common
RUN pip install --no-cache-dir /tmp/auth_common && rm -rf /tmp/auth_common

# Copy service code
COPY services/scan-session-service/app/ app/
COPY services/scan-session-service/tests/ tests/

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8000}"]
