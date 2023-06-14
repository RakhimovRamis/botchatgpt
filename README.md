# Telegram bot ChatGPT



```
$pip install aiohttp
$python3 main.py \
    <Telegram bot token> \
    <ChatGPT api key> \
    <your pin code>
```

Docker

```
$docker build . --tag chatbot
$docker run -d \
    -e TOKEN=<Telegram bot token> \
    -e API_KEY=<ChatGPT api key> \
    -e PINCODE=<your pin code> \
    chatbot

```