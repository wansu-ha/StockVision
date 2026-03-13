FROM python:3.13-slim

WORKDIR /app

COPY cloud_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sv_core/ sv_core/
COPY cloud_server/ cloud_server/

EXPOSE 4010

CMD ["uvicorn", "cloud_server.main:app", "--host", "0.0.0.0", "--port", "4010"]
