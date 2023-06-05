import os
import aiohttp
import asyncio
import logging
import json
 
URL = 'https://api.telegram.org/bot'
TOKEN_TG = os.getenv("TOKEN_TG")
TOKEN_CHATGPT = os.getenv("TOKEN_CHATGPT")
PINCODE = os.getenv("PINCODE")
logging.basicConfig(level=logging.INFO)
allowed_chat_id = []
history_message = {}
bot_message = {"start": "Приветствую! Я ChatGPT - ваш персональный бот для общения и помощи в различных вопросах, чтобы начать введите пин-код доступа.",
                "enter_pin_code": "Пожалуйста, введите верный пин-код для доступа к ChatGPT.",
                "correct_pin_code": "Доступ к ChatGPT разрешен, какую задачу вы хотите мне поручить?",
                "keyboard_clear": "Удалить историю"
            }

async def get_updates(session, offset=0):
    async with session.get(f'{URL}{TOKEN_TG}/getUpdates?offset={offset}') as response:
        updates = await response.json()
        return updates['result']
 
async def send_chat_action(session, chat_id):
    await session.get(f'{URL}{TOKEN_TG}/sendChatAction?chat_id={chat_id}&action=typing')
    
async def send_message(session, chat_id, text, reply_id):
    await session.get(f'{URL}{TOKEN_TG}/sendMessage?chat_id={chat_id}&text={text}&reply_to_message_id={reply_id}')

async def send_message_inline_keyboard(session, chat_id, text, reply_id):
    reply_markup = {'inline_keyboard': [[{'text': bot_message['keyboard_clear'], 'callback_data': 'history_clear'}]]}
    data = {'chat_id': chat_id, 'text': text, 'reply_to_message_id': reply_id, 'reply_markup': json.dumps(reply_markup), 'parse_mode': 'Markdown'}
    await session.post(f'{URL}{TOKEN_TG}/sendMessage', data=data)

async def chatgpt_api(session, chat_id):
    payload={'model': 'gpt-3.5-turbo', 'messages': history_message.get(chat_id), 'temperature': 0.8, 'max_tokens': 1024}
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {TOKEN_CHATGPT}'}
    async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload) as response:
        chatgpt_response = await response.json()
        return await escape_markdown(chatgpt_response['choices'][0]['message']['content'])
    
async def send_chatgpt_answer(session, chat_id, prompt, reply_id):
    history_message.setdefault(chat_id, []).append({"role": "user", "content": f"{prompt}"})
    answer = await chatgpt_api(session, chat_id)
    history_message.setdefault(chat_id, []).append({"role": "assistant", "content": f"{answer}"})
    logging.info(f'User id {chat_id} answer: {answer}')
    await send_message_inline_keyboard(session, chat_id, answer, reply_id)
 
async def callback_query(session, update):
    await session.get(f"{URL}{TOKEN_TG}/answerCallbackQuery?callback_query_id={update['callback_query']['id']}&text={bot_message['keyboard_clear']}")
    if update['callback_query']['data'] == 'history_clear':
        history_message.setdefault(update['callback_query']['message']['chat']['id'], []).clear()

async def escape_markdown(text):
    return text.replace('_', r'\_')\
                .replace('*', r'\*')\
                .replace('[', r'\[')                       

async def main():
    async with aiohttp.ClientSession() as session:
        update_id = 0
        update = await get_updates(session=session)
        if update:
            update_id = update[-1]['update_id']
        while True:
            await asyncio.sleep(1)
            updates = await get_updates(session=session, offset=update_id)
            tasks = []
            for update in updates:
                if update_id < update['update_id']:
                    update_id = update['update_id']
                    if update.get('callback_query'):
                        await callback_query(session, update)
                        break

                    logging.info(f"User id {update['message']['chat']['id']} message: {update['message'].get('text')}")
                    tasks.append(asyncio.create_task(send_chat_action(session=session, chat_id=update['message']['chat']['id'])))
                    if not update['message'].get('entities'):
                        if update['message']['chat']['id'] in allowed_chat_id:
                            tasks.append(asyncio.create_task(send_chatgpt_answer(session=session, chat_id=update['message']['chat']['id'],
                                                                                 prompt=update['message'].get('text'),
                                                                                 reply_id=update['message']['message_id'])))
                        else:
                            text = bot_message['enter_pin_code']
                            if update['message'].get('text') == PINCODE:
                                allowed_chat_id.append(update['message']['chat']['id'])
                                text = bot_message['correct_pin_code']
                            tasks.append(asyncio.create_task(send_message(session=session, chat_id=update['message']['chat']['id'],
                                                                          text=text,
                                                                          reply_id=update['message']['message_id'])))
                    else:
                        tasks.append(asyncio.create_task(send_message(session=session, chat_id=update['message']['chat']['id'],
                                                                      text=bot_message['start'],
                                                                      reply_id=update['message']['message_id'])))
            asyncio.gather(*tasks)
 
asyncio.run(main())