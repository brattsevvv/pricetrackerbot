import asyncio
from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)  # Telegram User ID
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    country = Column(String, default="FI")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tracked_products = relationship("TrackedProduct", back_populates="user", cascade="all, delete-orphan")

class TrackedProduct(Base):
    __tablename__ = "tracked_products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String, nullable=False)
    product_url = Column(String, nullable=False)
    best_price = Column(Float, nullable=False)
    base_price = Column(Float, nullable=True)
    delivery_fee = Column(Float, nullable=True)
    store_name = Column(String, nullable=False)
    store_link = Column(String, nullable=False)
    last_checked = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="tracked_products")

class Database:
    def __init__(self, db_url: str = "sqlite+aiosqlite:///bot.db"):
        if "sqlite" in db_url:
            try:
                from pathlib import Path
                clean_path = db_url.split("///")[-1]
                if clean_path and not clean_path.startswith(":memory:"):
                    Path(clean_path).resolve().parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_models(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None) -> User:
        async with self.session_factory() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                user = User(id=user_id, username=username, first_name=first_name)
                session.add(user)
                await session.commit()
                await session.refresh(user)
            return user

    async def add_tracked_product(
        self,
        user_id: int,
        product_name: str,
        product_url: str,
        best_price: float,
        base_price: float | None,
        delivery_fee: float | None,
        store_name: str,
        store_link: str
    ) -> TrackedProduct:
        async with self.session_factory() as session:
            # Check if already tracking this product URL for this user
            stmt = select(TrackedProduct).where(
                TrackedProduct.user_id == user_id,
                TrackedProduct.product_url == product_url
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.best_price = best_price
                existing.base_price = base_price
                existing.delivery_fee = delivery_fee
                existing.store_name = store_name
                existing.store_link = store_link
                existing.last_checked = datetime.utcnow()
                await session.commit()
                await session.refresh(existing)
                return existing
            
            product = TrackedProduct(
                user_id=user_id,
                product_name=product_name,
                product_url=product_url,
                best_price=best_price,
                base_price=base_price,
                delivery_fee=delivery_fee,
                store_name=store_name,
                store_link=store_link
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    async def get_user_tracked_products(self, user_id: int) -> list[TrackedProduct]:
        async with self.session_factory() as session:
            stmt = select(TrackedProduct).where(TrackedProduct.user_id == user_id).order_by(TrackedProduct.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_all_tracked_products(self) -> list[TrackedProduct]:
        async with self.session_factory() as session:
            stmt = select(TrackedProduct)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def delete_tracked_product(self, product_id: int, user_id: int) -> bool:
        async with self.session_factory() as session:
            stmt = select(TrackedProduct).where(
                TrackedProduct.id == product_id,
                TrackedProduct.user_id == user_id
            )
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            if product:
                await session.delete(product)
                await session.commit()
                return True
            return False

    async def update_product_price(
        self,
        product_id: int,
        new_price: float,
        base_price: float | None,
        delivery_fee: float | None,
        store_name: str,
        store_link: str
    ):
        async with self.session_factory() as session:
            stmt = select(TrackedProduct).where(TrackedProduct.id == product_id)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            if product:
                product.best_price = new_price
                product.base_price = base_price
                product.delivery_fee = delivery_fee
                product.store_name = store_name
                product.store_link = store_link
                product.last_checked = datetime.utcnow()
                await session.commit()
