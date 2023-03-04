from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app, stub

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200

def test_analyze():
    response = client.post("/analyze", json={
        "url": "https://news.ycombinator.com/",
        "recursive_mode": "BFS",
        "maintain_domain": True,
        "max_urls": 5,
        "save_to_azure": True,
        "azure_container_name": "testing",
    })
    assert response.status_code == 200
    print(response.json())

def test_analyze_many():
    response = client.post("/analyze-many", json={
        "urls": ["https://news.ycombinator.com/", "https://dagster.io/blog/chatgpt-langchain", "https://www.youtube.com/watch?v=Q8g9zL-JL8E"],
        "recursive_mode": "BFS",
        "maintain_domain": True,
        "max_urls": 5,
        "save_to_azure": True,
        "azure_container_name": "testing",
    })
    assert response.status_code
    for url, result in response.json().items():
        print(url + ": " + str(result))

def test_upload():
    response = client.post("/test-upload", json={
        "container_name": "testing",
        "file_path": "",
        "file_name": "test.txt",
        "contents": "Hello World!"
    })
    assert response.status_code == 200

if __name__ == "__main__":
    with stub.run():
        # test_root()
        # test_analyze()
        test_analyze_many()
        # test_upload()