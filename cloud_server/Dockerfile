FROM python:3.13-slim

WORKDIR /app

# sv_core를 먼저 복사 — requirements.txt의 -e ../sv_core가 이를 참조
COPY sv_core/ /app/sv_core/
COPY cloud_server/requirements.txt /app/cloud_server/requirements.txt

WORKDIR /app/cloud_server
RUN pip install --no-cache-dir -r requirements.txt

COPY cloud_server/ /app/cloud_server/

WORKDIR /app
EXPOSE 4010

CMD ["uvicorn", "cloud_server.main:app", "--host", "0.0.0.0", "--port", "4010"]
