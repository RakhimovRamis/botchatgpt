# Telegram bot ChatGPT

![output](https://github.com/RakhimovRamis/botchatgpt/assets/83058680/9c0cbf72-11ff-4a72-bae7-56ad578fe5c1)


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
