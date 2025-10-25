#!/usr/bin/env python3
"""
Telegram Bot для автоматической блокировки пользователей, отписавшихся от канала.

Этот бот специально разработан для Telegram каналов (не групп).
Он отслеживает подписчиков и блокирует тех, кто отписался.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
)
from telegram.constants import ChatMemberStatus

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Получаем конфигурацию из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

if not BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("Необходимо указать BOT_TOKEN и CHANNEL_ID в файле .env")

try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    raise ValueError("CHANNEL_ID должен быть числом")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Бот запущен и отслеживает отписки от канала.\n"
        "Пользователи, отписавшиеся от канала, будут автоматически заблокированы."
    )


async def track_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отслеживает изменения статуса подписчиков канала.
    Блокирует пользователей, которые отписались от канала.
    """
    try:
        # Получаем информацию об изменении статуса подписчика
        result = update.my_chat_member or update.chat_member

        if not result:
            return

        # Проверяем, что изменение произошло в нужном канале
        if result.chat.id != CHANNEL_ID:
            return

        old_status = result.old_chat_member.status
        new_status = result.new_chat_member.status
        user = result.new_chat_member.user

        # Игнорируем ботов
        if user.is_bot:
            return

        # Проверяем, отписался ли пользователь от канала
        # member = подписан, left = отписался
        unsubscribed = (
            old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            and new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]
        )

        if unsubscribed:
            try:
                # Блокируем пользователя в канале
                await context.bot.ban_chat_member(
                    chat_id=CHANNEL_ID,
                    user_id=user.id
                )

                logger.info(
                    f"Пользователь отписался и заблокирован: {user.full_name} "
                    f"(ID: {user.id}, Username: @{user.username or 'нет'}) "
                    f"| {old_status} (подписан) -> {new_status} (отписался)"
                )

            except Exception as e:
                logger.error(
                    f"Ошибка при блокировке пользователя {user.full_name} (ID: {user.id}): {e}"
                )

        # Логируем другие изменения статуса для отладки
        elif old_status != new_status:
            logger.info(
                f"Изменение статуса: {user.full_name} "
                f"(ID: {user.id}) | {old_status} -> {new_status}"
            )

    except Exception as e:
        logger.error(f"Ошибка в обработчике track_channel_member: {e}", exc_info=True)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику работы бота"""
    if not update.message:
        return

    await update.message.reply_text(
        f"Бот активен и мониторит канал ID: {CHANNEL_ID}\n"
        f"Время работы: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Произошла ошибка: {context.error}", exc_info=context.error)


def main() -> None:
    """Запуск бота"""
    logger.info("Запуск бота...")
    logger.info(f"Мониторинг канала с ID: {CHANNEL_ID}")

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))

    # Регистрируем обработчик изменений статуса подписчиков канала
    # ChatMemberHandler отслеживает подписки/отписки в канале
    # MY_CHAT_MEMBER - изменения статуса самого бота
    # CHAT_MEMBER - изменения статуса других пользователей (подписки/отписки)
    application.add_handler(
        ChatMemberHandler(track_channel_member, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    application.add_handler(
        ChatMemberHandler(track_channel_member, ChatMemberHandler.CHAT_MEMBER)
    )

    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    logger.info("Бот успешно запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
