import os
from enum import Enum as PyEnum

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, BigInteger, String, DateTime, select, update, func, text, Integer, Boolean, Enum as SQLEnum


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=True)
    reg_time = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    status_user = Column(String(64), default='user')
    language = Column(String(2), default='ru')
    subscription_end = Column(DateTime, nullable=True)
    parse_only_active = Column(Boolean, default=False, nullable=False)



class ParsingTaskStatus(PyEnum):
    NEW = 'new'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    ERROR = 'error'
    CANCELLED = 'cancelled'


class ParsingType(PyEnum):
    """Типы парсинга"""
    CHAT_MEMBERS = 'chat_members'          # Парсинг участников чата
    CHAT_WRITERS = 'chat_writers'          # Парсинг писавших в чат
    CHANNEL_COMMENTERS = 'channel_commenters'  # Парсинг комментаторов канала


class SystemAccountStatus(PyEnum):
    """Статусы системных аккаунтов"""
    OK = 'ok'                     # аккаунт работает нормально и свободен
    IS_BUSY = 'is_busy'           # аккаунт занят (выполняет задачу)
    AUTH_REQUIRED = 'auth_required'  # требуется авторизация (нужен номер телефона)
    BANNED = 'banned'             # аккаунт забанен
    FLOOD_WAIT = 'flood_wait'     # временная блокировка из-за флуда
    SESSION_EXPIRED = 'session_expired'  # сессия устарела


class ParsingTask(Base):
    __tablename__ = 'parsing_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(BigInteger, nullable=False)
    target_url = Column(String(500), nullable=False)
    parsing_type = Column(SQLEnum(ParsingType), default=ParsingType.CHAT_MEMBERS, nullable=False)  # тип парсинга
    status = Column(SQLEnum(ParsingTaskStatus), default=ParsingTaskStatus.NEW, nullable=False)  # new, processing, completed, error
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))



class SystemAccount(Base):
    __tablename__ = 'system_accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session = Column(String(255), nullable=False, unique=True)
    json = Column(String(255), nullable=False, unique=True)
    status = Column(SQLEnum(SystemAccountStatus), default=SystemAccountStatus.OK, nullable=False)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    payload = Column(String(255), nullable=False)
    telegram_payment_charge_id = Column(String(255), nullable=False)
    provider_payment_charge_id = Column(String(255), nullable=True)
    payment_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    status = Column(String(20), default='completed')


class DB_M:
    def __init__(self, db_uri):
        if not db_uri:
            raise ValueError('SQLALCHEMY_DATABASE_URL_TG не установлен в переменных окружения')
        
        if db_uri.startswith('sqlite'):
            self.engine = create_async_engine(
                db_uri, 
                echo=False
            )
        else:
            self.engine = create_async_engine(
                db_uri, 
                echo=False, 
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )


    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


    async def add_new_user(self, user_id, username, first_name, last_name, language='ru'):
        async with self.async_session() as session:
            # Проверяем, существует ли пользователь
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user is None:
                # Пользователь не существует, создаем нового
                new_user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language=language
                )
                session.add(new_user)
                await session.commit()


    async def get_user_by_id(self, user_id):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            return user


    async def get_status_user(self, user_id):
        """Получить статус пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User.status_user).where(User.user_id == user_id)
            )
            status_user = result.scalar_one_or_none()
            
            # Если пользователь не найден, возвращаем дефолтный статус 'user'
            if status_user is None:
                status_user = 'user'
            
            return status_user


    async def get_admins(self):
        """Получить всех админов бота"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(
                    (User.status_user == 'main_admin') | (User.status_user == 'admin')
                )
            )
            admins = result.scalars().all()
            
            return admins


    async def update_user(self, user_id, **kwargs) -> None:
        """Обновить информацию о пользователе"""
        async with self.async_session() as session:
            # Получаем текущего пользователя
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            # Обновляем поля, если они предоставлены
            if user:
                for key, value in kwargs.items():
                    if value is not None and hasattr(user, key):
                        setattr(user, key, value)
                
                await session.commit()
            else: 
                return


    async def count_users(self) -> int:
        """Получить кол-во всех пользователей"""
        async with self.async_session() as session:
            result = await session.execute(
                select(func.count(User.user_id))
            )
            count = result.scalar()
            
            return count


    async def get_users_id(self) -> list:
        """Получить id всех пользователей бота"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User.user_id)
            )
            users_id = result.scalars().all()
            
            return users_id


    async def add_payment(self, user_id, amount, currency, payload, telegram_payment_charge_id, provider_payment_charge_id=None, status='completed'):
        """Сохранить данные о платеже в базу"""
        async with self.async_session() as session:
            new_payment = Payment(
                user_id=user_id,
                amount=amount,
                currency=currency,
                payload=payload,
                telegram_payment_charge_id=telegram_payment_charge_id,
                provider_payment_charge_id=provider_payment_charge_id,
                status=status
            )
            session.add(new_payment)
            await session.commit()


    async def get_payments_by_user(self, user_id):
        """Получить данные о платежах пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Payment).where(Payment.user_id == user_id).order_by(Payment.payment_date.desc())
            )
            payments = result.scalars().all()
            
            # Возвращаем список словарей
            return [
                {
                    'id': p.id,
                    'user_id': p.user_id,
                    'amount': p.amount,
                    'currency': p.currency,
                    'payload': p.payload,
                    'telegram_payment_charge_id': p.telegram_payment_charge_id,
                    'provider_payment_charge_id': p.provider_payment_charge_id,
                    'payment_date': p.payment_date,
                    'status': p.status
                }
                for p in payments
            ]


    # ==================== ParsingTask методы ====================
    async def create_parsing_task(self, creator_id, target_url, parsing_type=ParsingType.CHAT_MEMBERS):
        """Создать новую задачу парсинга"""
        async with self.async_session() as session:
            new_task = ParsingTask(
                creator_id=creator_id,
                target_url=target_url,
                parsing_type=parsing_type,
                status=ParsingTaskStatus.NEW
            )
            session.add(new_task)
            await session.commit()
            await session.refresh(new_task)
            return new_task.id

    async def get_parsing_task(self, task_id):
        """Получить задачу парсинга по ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(ParsingTask).where(ParsingTask.id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_parsing_tasks_by_user(self, user_id):
        """Получить все задачи парсинга для пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(ParsingTask)
                .where(ParsingTask.creator_id == user_id)
                .order_by(ParsingTask.created_at.desc())
            )
            return result.scalars().all()

    async def get_active_parsing_tasks_by_user(self, user_id):
        """Получить активные задачи парсинга для пользователя (NEW или PROCESSING)"""
        async with self.async_session() as session:
            result = await session.execute(
                select(ParsingTask)
                .where(
                    (ParsingTask.creator_id == user_id) &
                    (ParsingTask.status.in_([ParsingTaskStatus.NEW, ParsingTaskStatus.PROCESSING]))
                )
                .order_by(ParsingTask.created_at.desc())
            )
            return result.scalars().all()

    async def get_new_parsing_tasks(self):
        """Получить все новые задачи парсинга"""
        async with self.async_session() as session:
            result = await session.execute(
                select(ParsingTask)
                .where(ParsingTask.status == ParsingTaskStatus.NEW)
                .order_by(ParsingTask.created_at)
            )
            return result.scalars().all()

    async def update_parsing_task_status(self, task_id, status):
        """Обновить статус задачи парсинга и опционально путь к файлу с результатом"""
        async with self.async_session() as session:
            result = await session.execute(
                select(ParsingTask).where(ParsingTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = status
                await session.commit()

    async def cancel_parsing_task(self, task_id, user_id=None):
        """Отменить задачу парсинга (только если она принадлежит пользователю и активна)"""
        async with self.async_session() as session:
            # Получаем задачу
            result = await session.execute(
                select(ParsingTask).where(ParsingTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return False, "Задача не найдена"
            
            # Проверяем принадлежность пользователю, если указан user_id
            if user_id is not None and task.creator_id != user_id:
                return False, "Задача не принадлежит вам"
            
            # Проверяем, можно ли отменить (только NEW или PROCESSING)
            if task.status not in (ParsingTaskStatus.NEW, ParsingTaskStatus.PROCESSING):
                return False, f"Задача уже завершена (статус: {task.status.value})"
            
            # Меняем статус на CANCELLED
            task.status = ParsingTaskStatus.CANCELLED
            await session.commit()
            return True, "Задача успешно отменена"


    # ==================== SystemAccount методы ====================
    async def get_free_system_account(self):
        """Получить свободную системную учетную запись (status=OK)"""
        async with self.async_session() as session:
            result = await session.execute(
                select(SystemAccount)
                .where(SystemAccount.status == SystemAccountStatus.OK)
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_system_account_by_session(self, session_path):
        """Получить системную учетную запись по пути к сессии"""
        async with self.async_session() as session:
            result = await session.execute(
                select(SystemAccount)
                .where(SystemAccount.session == session_path)
            )
            return result.scalar_one_or_none()

    async def create_system_account(self, session_path, json_path):
        """Добавить новый аккаунт в БД"""
        async with self.async_session() as session:
            # Проверяем, если аккаунт уже создан
            existing = await self.get_system_account_by_session(session_path)
            if existing:
                return existing.id
            
            new_account = SystemAccount(
                session=session_path,
                json=json_path,
                status=SystemAccountStatus.OK
            )
            session.add(new_account)
            await session.commit()
            await session.refresh(new_account)
            return new_account.id

    async def set_system_account_status(self, session_path, status):
        """Установить статус системной учетной записи"""
        async with self.async_session() as session:
            result = await session.execute(
                select(SystemAccount).where(SystemAccount.session == session_path)
            )
            account = result.scalar_one_or_none()
            
            if account:
                account.status = status
                await session.commit()

    async def get_all_system_accounts(self):
        """Получить все системные учетные записи"""
        async with self.async_session() as session:
            result = await session.execute(
                select(SystemAccount).order_by(SystemAccount.id)
            )
            return result.scalars().all()

    async def scan_accounts(self, accounts_dir='accounts/'):
        """Сканировать папку accounts/ на наличие папок аккаунтов и сохранить пути в БД"""
        accounts_added = []
        if not os.path.exists(accounts_dir):
            return accounts_added
        
        for item in os.listdir(accounts_dir):
            item_path = os.path.join(accounts_dir, item)
            if os.path.isdir(item_path):
                session_file = None
                json_file = None
                for file in os.listdir(item_path):
                    file_path = os.path.join(item_path, file)
                    if file.endswith('.session'):
                        session_file = file_path
                    elif file.endswith('.json'):
                        json_file = file_path
                if session_file and json_file:
                    account_id = await self.create_system_account(session_file, json_file)
                    accounts_added.append(account_id)
        return accounts_added

    async def get_free_account(self):
        """Получить свободный аккаунт (status=OK) и пометить его как занятый (IS_BUSY)"""
        async with self.async_session() as session:
            result = await session.execute(
                select(SystemAccount)
                .where(SystemAccount.status == SystemAccountStatus.OK)
                .limit(1)
            )
            account = result.scalar_one_or_none()
            if account:
                account.status = SystemAccountStatus.IS_BUSY
                await session.commit()
            return account