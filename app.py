import os
from litestar import Litestar, get, post, MediaType
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import Server
from litestar.config.cors import CORSConfig
from pydantic import BaseModel
from meilisearch import Client

# Initialize MeiliSearch client
meili_client = Client('https://meilisearch.k3s.koski.co', os.environ.get("MEILI_API_KEY"))

class QueryModel(BaseModel):
    q: str

class SalesResponseModel(BaseModel):
    upc: str
    description: str
    promo: float
    regular: float
    discountPercent: float

@get("/sales", media_type=MediaType.TEXT)
async def get_sales() -> str:
    idx = meili_client.index('items')
    search_results = idx.search('', {
        'sort': ['discountPercent:desc'],
        'filter': ['stockLevel IN [HIGH, LOW]'],
        'limit': 200,
    })
    results = "\n".join([f"{hit['description']}\t{100*round(hit['discountPercent'])}% off\t${hit['promo']}" for hit in search_results['hits']])
    return results

@post("/query")
async def search_query(data: QueryModel) -> list[dict]:
    search_results = meili_client.index('items').search(data.q, {
        'filter': ['stockLevel IN [HIGH, LOW]'],
        'limit': 50,
    })
    results = [{'upc': hit['upc'], 'description': hit['description'], 'promo': hit['promo'], 'regular': hit['regular'], 'discountPercent': hit['discountPercent']} for hit in search_results['hits']]
    return results

cors_config = CORSConfig(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app = Litestar([get_sales, search_query], cors_config=cors_config, openapi_config=OpenAPIConfig(title="Grocery RestAPI", version="1.0.0", servers=[Server(url="https://grocery-restapi.k3s.koski.co")]))
# app = Litestar([get_sales, search_query], cors_config=cors_config, openapi_config=OpenAPIConfig(title="Grocery RestAPI", version="1.0.0"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)