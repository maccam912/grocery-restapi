from litestar import LiteStar, Path
from pydantic import BaseModel
from meilisearch import Client

# Initialize MeiliSearch client
meili_client = Client('https://meilisearch.k3s.koski.co', '<apitoken>')

app = LiteStar()

class QueryModel(BaseModel):
    query: str

class SalesResponseModel(BaseModel):
    id: str
    title: str
    percentage_off: float

@app.route("/sales", methods=["GET"])
async def get_sales():
    search_results = meili_client.index('products').search('', {
        'sort': ['discountPercentage:desc']  # Sort by percentage_off in descending order
    })
    results = [SalesResponseModel(id=hit['id'], title=hit['title'], percentage_off=hit['percentage_off']) for hit in search_results['hits']]
    return results

@app.route("/query", methods=["POST"])
async def search_query(request):
    body = await request.json()
    query_data = QueryModel(**body)
    search_results = meili_client.index('your_index').search(query_data.query)
    # Assuming the documents have 'id' and 'title' fields
    results = [{'id': hit['id'], 'title': hit['title']} for hit in search_results['hits']]
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)