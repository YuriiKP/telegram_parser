from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, BigInteger, String, DateTime, select, update, func, text, Integer

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
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(
                    (User.status_user == 'main_admin') | (User.status_user == 'admin')
                )
            )
            admins = result.scalars().all()
            
            return admins


    async def update_user(self, user_id, **kwargs) -> None:
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
        async with self.async_session() as session:
            result = await session.execute(
                select(func.count(User.user_id))
            )
            count = result.scalar()
            
            return count


    async def get_users_id(self) -> list:
        async with self.async_session() as session:
            result = await session.execute(
                select(User.user_id)
            )
            users_id = result.scalars().all()
            
            return users_id


    async def add_payment(self, user_id, amount, currency, payload, telegram_payment_charge_id, provider_payment_charge_id=None, status='completed'):
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