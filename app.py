import os
from litestar import Litestar, get, post
from pydantic import BaseModel
from meilisearch import Client

# Initialize MeiliSearch client
meili_client = Client('https://meilisearch.k3s.koski.co', os.environ.get("MEILI_API_KEY"))

class QueryModel(BaseModel):
    q: str

class SalesResponseModel(BaseModel):
    id: str
    title: str
    percentage_off: float

@get("/sales")
async def get_sales() -> list[SalesResponseModel]:
    search_results = meili_client.index('products').search('', {
        'sort': ['discountPercentage:desc']  # Sort by percentage_off in descending order
    })
    results = [SalesResponseModel(id=hit['id'], title=hit['title'], percentage_off=hit['percentage_off']) for hit in search_results['hits']]
    return results

@post("/query")
async def search_query(request: QueryModel) -> list[dict]:
    search_results = meili_client.index('your_index').search(request.query)
    # Assuming the documents have 'id' and 'title' fields
    results = [SalesResponseModel(id=hit['id'], title=hit['title']) for hit in search_results['hits']]
    return results

app = Litestar([get_sales, search_query])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)