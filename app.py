from typing import Optional, List
from enum import Enum
import os
import structlog
import logging
from litestar import Litestar, post
from litestar.status_codes import HTTP_200_OK
from litestar.openapi import OpenAPIConfig
from litestar.config.cors import CORSConfig
from litestar.di import Provide
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from litestar import Response

"""
This module defines the structure and functionality for a grocery store's REST API.
It includes models for item search requests and responses, database session management,
and the endpoint for searching items on sale.
"""

structlog.configure(
    processors=[
        structlog.processors.KeyValueRenderer(
            key_order=["timestamp", "level", "event", "context"]
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logging.basicConfig(level=logging.DEBUG)

logger = structlog.get_logger()

DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
logger.info("Creating database engine", database_url=DATABASE_URL)
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)
Base = declarative_base()


class Category(str, Enum):
    Adult_Beverage = "Adult Beverage"
    Apparel = "Apparel"
    Automotive = "Automotive"
    Baby = "Baby"
    Bakery = "Bakery"
    Baking_Goods = "Baking Goods"
    Beauty = "Beauty"
    Bed_Bath = "Bed & Bath"
    Beverages = "Beverages"
    Breakfast = "Breakfast"
    Candy = "Candy"
    Canned_Packaged = "Canned & Packaged"
    Cleaning_Products = "Cleaning Products"
    Condiment_Sauces = "Condiment & Sauces"
    Dairy = "Dairy"
    Deli = "Deli"
    Easter = "Easter"
    Electronics = "Electronics"
    Entertainment = "Entertainment"
    Floral = "Floral"
    Frozen = "Frozen"
    Garden_Patio = "Garden & Patio"
    Gift_Cards = "Gift Cards"
    Hardware = "Hardware"
    Health = "Health"
    Holiday_Seasonal_Goods = "Holiday & Seasonal Goods"
    Home_Decor = "Home Decor"
    International = "International"
    Kitchen = "Kitchen"
    Meat_Seafood = "Meat & Seafood"
    Natural_Organic = "Natural & Organic"
    Office_School_Crafts = "Office, School, & Crafts"
    Other = "Other"
    Party = "Party"
    Pasta_Sauces_Grain = "Pasta, Sauces, Grain"
    Personal_Care = "Personal Care"
    Pet_Care = "Pet Care"
    Produce = "Produce"
    Snacks = "Snacks"
    Sporting_Goods = "Sporting Goods"
    Tobacco = "Tobacco"
    Travel_Luggage = "Travel & Luggage"
    Valentines_Day = "Valentine's Day"


class ItemSearchRequest(BaseModel):
    """
    A model representing a request for searching items.

    Parameters
    ----------
    category : Optional[Category]
        The category to filter items by.
    description : Optional[str]
        A keyword to search in the item descriptions.
    on_sale : Optional[bool]
        A flag to filter items that are on sale.
    in_stock: Optional[str] = None
    """

    category: Optional[Category] = None
    description: Optional[str] = None
    on_sale: bool = True
    in_stock: Optional[str] = None


class Item(BaseModel):
    """
    A model representing an item in the inventory.

    Parameters
    ----------
    category : str
        The category of the item.
    description : str
        The description of the item.
    promo_price : Optional[float]
        The promotional price of the item. Can be None.
    regular_price : Optional[float]
        The regular price of the item. Can be None.
    stock_level : Optional[str] = None
        The stock level of the item. Can be None if the stock level is unknown.
    upc : str
        The UPC of the item.
    discount_percent : Optional[float] = None
        The discount percentage of the item. Can be None.
    """

    category: str
    description: str
    promo_price: Optional[float] = None
    regular_price: Optional[float] = None
    stock_level: Optional[str] = None
    upc: str
    discount_percent: Optional[float] = None


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
    response_class=Response,
    dependencies={"db": Provide(get_db_session)},
    status_code=HTTP_200_OK,
)
async def search(data: ItemSearchRequest, db: AsyncSession) -> Response:
    """
    Endpoint for searching items based on the provided criteria, responding with CSV formatted plaintext.

    Parameters
    ----------
    request : ItemSearchRequest
        The search criteria.
    db : AsyncSession
        The database session.

    Returns
    -------
    Response
        The search results containing items that match the criteria, formatted as CSV.
    """
    logger.debug("Search request received", request=data.dict())
    async with db as session:
        base_query = "SELECT category, description, promo_price, regular_price, stock_level, upc, discount_percent FROM public.items_view"
        conditions = []
        if data.on_sale:
            conditions.append("promo_price > 0")

        if data.category:
            conditions.append(f"category = '{data.category.value}'")
            logger.debug("Filtering by category", category=data.category.value)

        if data.description:
            ts_query = "to_tsvector('english', description) @@ plainto_tsquery('english', :description)"
            conditions.append(ts_query)
            logger.debug("Filtering by description", description=data.description)

        if data.in_stock:
            if data.in_stock in ["HIGH", "LOW"]:
                conditions.append(f"stock_level = '{data.in_stock}'")
                logger.debug("Filtering by stock level", stock_level=data.in_stock)
            else:
                logger.error("Invalid stock level value", stock_level=data.in_stock)
                raise ValueError("Invalid stock level value. Must be 'HIGH' or 'LOW'.")

        where_clause = " AND ".join(conditions)
        if where_clause:
            base_query += " WHERE " + where_clause

        base_query += " ORDER BY discount_percent DESC LIMIT 500"

        result = await session.execute(
            text(base_query), {"description": data.description}
        )
        items = result.fetchall()
        logger.info("Search query executed", items_count=len(items))

        # Format results as CSV
        csv_data = "Description\tDiscount Percent\tUPC\n" + "\n".join(
            [
                f"{item[1]}\t{item[6] if item[6] is not None else ''}\t{item[5]}"
                for item in items
            ]
        )

        return Response(content=csv_data, media_type="text/plain")


cors_config = CORSConfig(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app = Litestar(
    [search],
    cors_config=cors_config,
    openapi_config=OpenAPIConfig(
        title="Grocery RestAPI",
        version="1.0.0",
        # servers=[Server(url="https://grocery-restapi.k3s.koski.co")],
    ),
)

if __name__ == "__main__":
    logger.info("Starting application", host="0.0.0.0", port=8080)
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
