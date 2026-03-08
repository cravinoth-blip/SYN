"""
Test script to query the local FastAPI RAG server.
Run app.py first: uvicorn app:app --host 0.0.0.0 --port 8000
Then run this script to test queries.
"""

import requests
import json
import sys

API_URL = "http://localhost:8000/query/"

def query(text, top_k=5):
    response = requests.post(API_URL, json={
        "query_text": text,
        "top_k": top_k,
        "table_name": "RAG_TEST"
    })

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return

    data = response.json()
    results = data.get("context", [])

    print(f"\nQuery: '{text}'")
    print(f"Results: {len(results)}")
    print("-" * 60)

    for i, item in enumerate(results):
        similarity = item.get('SIMILARITY', 0)
        title = item.get('TITLE', 'N/A')
        source = item.get('SOURCE_FILE', 'N/A')
        text_preview = item.get('TEXT', '')[:200]
        page = item.get('PAGE_REFERENCE', 'N/A')

        print(f"\n[{i+1}] Score: {similarity:.4f}")
        print(f"    Title:  {title}")
        print(f"    Source: {source} ({page})")
        print(f"    Text:   {text_preview}...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
    else:
        query_text = input("Enter your query: ")

    query(query_text)
