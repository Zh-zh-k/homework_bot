import requests
import time

import os
import sys
import logging

import telegram

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка переменных окружения."""
    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        logging.critical('Переменные окружения отсутствуют')
    return (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        chat_id = TELEGRAM_CHAT_ID
        bot.send_message(chat_id, message)
        logging.debug('Сообщение отправлено')
    except Exception:
        logging.error('Ошибка отправки сообщения')
        raise Exception('Ошибка отправки сообщения')


def get_api_answer(timestamp):
    """Получение ответа от API."""
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})
        logging.debug('Ответ получен')
        if response.status_code != 200:
            logging.error('Ошибка статуса')
            raise Exception('Ошибка статуса')
    except requests.RequestException as error:
        logging.error('Нет доступа к ENDPOINT')
        raise error('Нет доступа к ENDPOINT')
    return response.json()


def check_response(response):
    """Проверка ответов."""
    if not isinstance(response, dict):
        raise TypeError('response не относится к типу dict')
    if 'homeworks' not in response:
        logging.error('Отсутствие ключа homeworks')
        raise Exception('Отсутствие ключа "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В ключ вложен не список')
    return response['homeworks']


def parse_status(homework):
    """Выдача статуса работы."""
    if 'status' in homework:
        homework_status = homework.get('status')
    else:
        logging.error('Нет ключа status')
        raise KeyError('Недокументированный статус домашшней работы')
    if 'homework_name' in homework:
        homework_name = homework.get('homework_name')
    else:
        logging.error('Нет ключа homework_name')
        raise KeyError('Нет ключа homework_name')
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Неожиданный статус домашней работы')
        raise Exception('Неизвестный статус')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Переменные окружения отсутствуют', exc_info=True)
        sys.exit('Токены переменных окружения отсутствуют')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - RETRY_PERIOD
    current_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            if len(homeworks) > 0:
                logging.debug('Новый статус у работы!')
                homework = homeworks[0]
                message = parse_status(homework)
                if current_message != message:
                    send_message(bot, message)
                    current_message = message
                    timestamp = response.get('current_date')
            else:
                logging.debug('Нет новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != current_message:
                send_message(bot, message)
                current_message = message
                logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
