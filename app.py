from typing import Optional, List
import os
from litestar import Litestar, post
from litestar.openapi.spec import Server
from litestar.openapi import OpenAPIConfig
from litestar.config.cors import CORSConfig
from litestar.di import Provide
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

"""
This module defines the structure and functionality for a grocery store's REST API.
It includes models for item search requests and responses, database session management,
and the endpoint for searching items on sale.
"""

DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)
Base = declarative_base()


class ItemSearchRequest(BaseModel):
    """
    A model representing a request for searching items.

    Parameters
    ----------
    category : Optional[str]
        The category to filter items by.
    description : Optional[str]
        A keyword to search in the item descriptions.
    on_sale : Optional[bool]
        A flag to filter items that are on sale.
    """

    category: Optional[str] = None
    description: Optional[str] = None
    on_sale: Optional[bool] = True


class Item(BaseModel):
    """
    A model representing an item in the inventory.

    Parameters
    ----------
    category : str
        The category of the item.
    description : str
        The description of the item.
    promo_price : float
        The promotional price of the item.
    regular_price : float
        The regular price of the item.
    stock_level : str
        The stock level of the item.
    upc : str
        The UPC of the item.
    discount_percent : float
        The discount percentage of the item.
    """

    category: str
    description: str
    promo_price: float
    regular_price: float
    stock_level: str
    upc: str
    discount_percent: float


class ItemSearchResponse(BaseModel):
    """
    A model representing the response to an item search request.

    Parameters
    ----------
    items : List[Item]
        A list of items matching the search criteria.
    """

    items: List[Item]


async def get_db_session():
    """
    Generator function that provides a database session.

    Yields
    ------
    AsyncSession
        An asynchronous session to the database.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


@post(
    "/sales",
    response_model=ItemSearchResponse,
    dependencies={"db": Provide(get_db_session)},
)
async def search(request: ItemSearchRequest, db: AsyncSession) -> ItemSearchResponse:
    """
    Endpoint for searching items based on the provided criteria.

    Parameters
    ----------
    request : ItemSearchRequest
        The search criteria.
    db : AsyncSession
        The database session.

    Returns
    -------
    ItemSearchResponse
        The search results containing items that match the criteria.
    """
    async with db as session:
        query = "SELECT * FROM public.items_view WHERE discount_percent > 0"
        if request.category:
            query += f" AND category = '{request.category}'"
        if request.description:
            query += f" AND description LIKE '%{request.description}%'"
        if not request.on_sale:
            query = query.replace("WHERE discount_percent > 0", "")

        result = await session.execute(text(query))
        items = result.fetchall()
        return ItemSearchResponse(items=[Item(**item) for item in items])


cors_config = CORSConfig(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app = Litestar(
    [search],
    cors_config=cors_config,
    openapi_config=OpenAPIConfig(title="Grocery RestAPI", version="1.0.0"),
    servers=[Server(url="https://grocery-restapi.k3s.koski.co")],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
