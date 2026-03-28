FROM python:3.13-slim

WORKDIR /app

COPY backtest_server/requirements.txt /app/backtest_server/requirements.txt
RUN pip install --no-cache-dir -r backtest_server/requirements.txt

COPY sv_core/ /app/sv_core/
COPY backtest_server/ /app/backtest_server/

EXPOSE 4040

CMD ["uvicorn", "backtest_server.main:app", "--host", "0.0.0.0", "--port", "4040"]
