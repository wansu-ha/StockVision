FROM python:3.13-slim

WORKDIR /app

COPY data_server/requirements.txt /app/data_server/requirements.txt
RUN pip install --no-cache-dir -r data_server/requirements.txt

COPY sv_core/ /app/sv_core/
COPY data_server/ /app/data_server/

EXPOSE 4030

CMD ["uvicorn", "data_server.main:app", "--host", "0.0.0.0", "--port", "4030"]
