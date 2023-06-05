FROM python:3.9-slim
WORKDIR /app
COPY main.py /app
RUN pip install aiohttp
ENTRYPOINT ["python", "main.py"]