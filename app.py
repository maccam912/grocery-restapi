import os
from litestar import Litestar, get, post
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

@get("/sales")
async def get_sales() -> list[SalesResponseModel]:
    idx = meili_client.index('items')
    search_results = idx.search('', {
        'sort': ['discountPercent:desc'],
        'filter': ['stockLevel IN [HIGH, LOW]'],
        'limit': 1000,
    })
    results = [SalesResponseModel(upc=hit['upc'], description=hit['description'], promo=hit['promo'], regular=hit['regular'], discountPercent=hit['discountPercent']) for hit in search_results['hits']]
    return results

@post("/query")
async def search_query(request: QueryModel) -> list[dict]:
    search_results = meili_client.index('items').search(request.query, {
        'filter': ['stockLevel IN [HIGH, LOW]'],
        'limit': 50,
    })
    results = [{'upc': hit['upc'], 'description': hit['description'], 'promo': hit['promo'], 'regular': hit['regular'], 'discountPercent': hit['discountPercent']} for hit in search_results['hits']]
    return results

app = Litestar([get_sales, search_query])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)