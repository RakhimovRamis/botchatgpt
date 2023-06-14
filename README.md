# Telegram bot ChatGPT



https://github.com/RakhimovRamis/botchatgpt/assets/83058680/699da493-0e6d-4239-af4a-5d8f41002697



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
