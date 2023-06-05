# Telegram bot ChatGPT

```
$docker build . --tag chatbot
$docker run -d \
    -e TOKEN_TG=<Telegram bot api key> \
    -e TOKEN_CHATGPT=<ChatGPT api key> \
    -e PINCODE=<your pin code access chatgpt> \
    chatbot

```