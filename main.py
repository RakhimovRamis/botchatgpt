import aiohttp
import asyncio
import logging
import json
import sys
import os
import re

logging.basicConfig(level=logging.INFO)
allowed_chat_id = []
history_message = {}
bot_message = {
    "start": "Приветствую! Я ChatGPT - ваш персональный бот для общения и помощи в различных вопросах, чтобы начать введите пин-код доступа.",
    "enter_pin_code": "Пожалуйста, введите верный пин-код для доступа к ChatGPT.",
    "correct_pin_code": "Доступ к ChatGPT разрешен, какую задачу вы хотите мне поручить?",
    "keyboard_clear": "Удалить историю"
}

class TBotAPI:
    URL = 'https://api.telegram.org/bot'
 
    def __init__(self, token):
        self.token = token
 
    async def get_updates(self, offset=0):
        await asyncio.sleep(.5)
        async with self.session.get(f'{self.URL}{self.token}/getUpdates?offset={offset}') as response:
            updates = await response.json()
            return updates['result']
 
    async def send_chat_action(self, chat_id):
        await self.session.get(f'{self.URL}{self.token}/sendChatAction?chat_id={chat_id}&action=typing')
    
    async def _send_message(self, method_name, data):
        async with self.session.post(f'{self.URL}{self.token}/{method_name}', data=data) as response:
            result = await response.json()
            return result

    async def send_message(self, chat_id, text, reply_id, reply_markup=None):
        data = {'chat_id': chat_id, 'text': await Utils.escape_markdown(text),
                'reply_to_message_id': reply_id, 'parse_mode': 'MarkdownV2'
            }
        return await self._send_message('sendMessage', data)
    
    async def edit_messgae_text(self, chat_id, text, message_id, reply_markup=None):
        data = {'chat_id': chat_id, 'text': await Utils.escape_markdown(text),
                'message_id': message_id, 'reply_markup': json.dumps(reply_markup),
                'parse_mode': 'MarkdownV2'
            }
        return await self._send_message('editMessageText', data)

    async def inline_keyboard(self):
        return {'inline_keyboard': [[{'text': bot_message['keyboard_clear'], 'callback_data': 'history_clear'}]]}
 
    async def callback_query(self, update):
        await self.session.get(f"{self.URL}{self.token}/answerCallbackQuery?callback_query_id={update['callback_query']['id']}&text={bot_message['keyboard_clear']}")
        if update['callback_query']['data'] == 'history_clear':
            history_message.setdefault(update['callback_query']['message']['chat']['id'], []).clear()
 
class ChatGPT(TBotAPI):
    def __init__(self, token, api_key):
        super().__init__(token)
        self.api_key = api_key

    async def response_stream(self, chat_id):
        payload={'model': 'gpt-3.5-turbo', 'messages': history_message.get(chat_id), 'temperature': 0.8, 'max_tokens': 1024, 'stream': True}
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
        async with self.session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload) as response:
            async for line in response.content:
                yield line

    async def send_content_stream(self, chat_id, prompt, reply_id):
        history_message.setdefault(chat_id, []).append({"role": "user", "content": f"{prompt}"})
        chunks = []
        message_id = None
        async for _chunk in self.response_stream(chat_id):
            chunk = _chunk.decode('utf-8')[6:]
            if chunk and not chunk.startswith('[DONE]'):
                chunk = json.loads(str(chunk))
                chunks.append(chunk)
                if not len(chunks) % 8 or chunk['choices'][0]['finish_reason'] == 'stop':
                    content = "".join([ch['choices'][0]['delta'].get('content', '') for ch in chunks])
                    if not message_id:
                        response = await self.send_message(chat_id, content, reply_id, await self.inline_keyboard())
                        message_id = response['result']['message_id']
                    else:
                        await self.edit_messgae_text(chat_id, content, message_id, await self.inline_keyboard())
        history_message.setdefault(chat_id, []).append({"role": "assistant", "content": content})
        logging.info(f'User id {chat_id} answer: {content}')

class Utils:
    @staticmethod
    async def escape_markdown(text):
        escape_chars = '([\\\\_\\*\\[\\]\\(\\)\\~>\\#\\+\\-=\\|\\{\\}\\.!])'
        return re.sub(escape_chars, r"\\\1", text)

class ChatBot(ChatGPT):
    def __init__(self, token, api_key, pincode):
        super().__init__(token, api_key)
        self.pincode = pincode

    async def create_message_tasks(self, update, tasks):
        chat_id = update['message']['chat']['id']
        message_id = update['message']['message_id']
        message_text = update['message'].get('text')
        entities = update['message'].get('entities')

        logging.info(f"User id {chat_id} message: {message_text}")
        tasks.append(asyncio.create_task(self.send_chat_action(chat_id=chat_id)))
        if entities and entities[0]['type'] == 'bot_command':
            coroutine = self.send_message(chat_id=chat_id, text=bot_message['start'], reply_id=message_id)
            tasks.append(asyncio.create_task(coroutine))
        else:
            if chat_id in allowed_chat_id:
                coroutine = self.send_content_stream(chat_id=chat_id, prompt=message_text, reply_id=message_id)
                tasks.append(asyncio.create_task(coroutine))
            else:
                text = bot_message['enter_pin_code']
                if message_text == self.pincode:
                    allowed_chat_id.append(chat_id)
                    text = bot_message['correct_pin_code']
                coroutine = self.send_message(chat_id=chat_id, text=text, reply_id=message_id)
                tasks.append(asyncio.create_task(coroutine))
        return tasks

    async def main(self):
        async with aiohttp.ClientSession() as session:
            self.session = session
            update_id = 0
            update = await self.get_updates()
            if update:
                update_id = update[-1]['update_id']
            while True:
                await asyncio.sleep(1)
                try:
                    updates = await self.get_updates(offset=update_id)
                    tasks = []
                    for update in updates:
                        if update_id < update['update_id']:
                            update_id = update['update_id']
                            if update.get('callback_query'):
                                await self.callback_query(update)
                                break
                            if update.get('message'): #my_chat_member
                                tasks = await self.create_message_tasks(update, tasks)
                    asyncio.gather(*tasks)
                except aiohttp.ClientConnectorError as e:
                    logging.error(e)
 
if __name__ == '__main__':
    token = os.getenv("TOKEN") or sys.argv[1]
    api_key = os.getenv("API_KEY") or sys.argv[2]
    pincode = os.getenv("PINCODE") or sys.argv[3]
    bot = ChatBot(token, api_key, pincode)
    asyncio.run(bot.main())