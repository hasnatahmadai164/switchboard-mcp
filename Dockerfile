FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "switchboard.server"]
