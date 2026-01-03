import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from loader import bot, db_manage
from storage import User


async def check_expired_subscriptions():
    """Проверяет истекшие подписки и отправляет уведомления"""
    print(f"[{datetime.now()}] Начало проверки истекших подписок...")
    
    async with db_manage.async_session() as session:
        # Получаем всех пользователей с активной подпиской (subscription_end не None)
        result = await session.execute(
            select(User).where(User.subscription_end.is_not(None))
        )
        users = result.scalars().all()
        
        expired_count = 0
        for user in users:
            # Проверяем, истекла ли подписка
            if user.subscription_end < datetime.now():
                try:
                    # Отправляем уведомление
                    await bot.send_message(
                        chat_id=user.user_id,
                        text="⚠️ Ваша подписка истекла! Пожалуйста, продлите её, чтобы продолжить пользоваться ботом."
                    )
                    
                    # Обновляем статус подписки в базе данных
                    await session.execute(
                        update(User)
                        .where(User.user_id == user.user_id)
                        .values(subscription_end=None)
                    )
                    await session.commit()
                    
                    print(f"Уведомление отправлено пользователю {user.user_id}")
                    expired_count += 1
                    
                except Exception as e:
                    print(f"Ошибка при отправке уведомления пользователю {user.user_id}: {e}")
                    await session.rollback()
    
    print(f"[{datetime.now()}] Проверка истекших подписок завершена. Найдено истекших: {expired_count}")


async def start_subscription_checker():
    """Запускает фоновую проверку подписок"""
    scheduler = AsyncIOScheduler()
    
    # Настраиваем задачу на выполнение раз в час
    scheduler.add_job(
        check_expired_subscriptions,
        trigger=IntervalTrigger(hours=1),
        id='subscription_checker',
        name='Проверка истекших подписок',
        replace_existing=True
    )
    
    # Запускаем планировщик
    scheduler.start()
    print("Фоновая проверка подписок запущена (раз в час)")
    
    # Бесконечный цикл для проверки работы
    # while True:
    #     await asyncio.sleep(3600)