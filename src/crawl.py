from fastapi.testclient import TestClient
from main import app, stub

client = TestClient(app)

initial_urls = [
    # wikipedia
    "https://en.wikipedia.org/wiki/SpaceX",
    "https://en.wikipedia.org/wiki/Elon_Musk",
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "https://en.wikipedia.org/wiki/Rust_(programming_language)",
    "https://en.wikipedia.org/wiki/NASA",
    "https://en.wikipedia.org/wiki/Mark_Zuckerberg",
    "https://en.wikipedia.org/wiki/Peregrine_falcon",
    "https://en.wikipedia.org/wiki/Bill_Gates",
    "https://en.wikipedia.org/wiki/Tel_Aviv",
    "https://en.wikipedia.org/wiki/Sushi",
    # Youtube
    "https://www.youtube.com/watch?v=Q8g9zL-JL8E",
    "https://www.youtube.com/watch?v=D6mgVOF2Ov8",
    "https://www.youtube.com/watch?v=aypufy2HyA8",
    "https://www.youtube.com/watch?v=EuNguMnSKnA",
    "https://www.youtube.com/watch?v=J9oEc0wCQDE&t=10927s",
    "https://www.youtube.com/watch?v=RFsIWtmc-WA",
    "https://www.youtube.com/watch?v=0lJKucu6HJc",
    "https://www.youtube.com/watch?v=rSTu1I5t700",
    "https://www.youtube.com/watch?v=OmDn0JZIpoY",
    "https://www.youtube.com/watch?v=hbxQw4LQwws",
    # Misc.
    "https://dagster.io/blog/chatgpt-langchain",
    "https://news.ycombinator.com/",
    "https://sethkim.me/l/",
    "https://alexgraveley.com/",
    "https://shreyjoshi.com/",
    "https://www.crmarsh.com/",
    "https://www.amnh.org/",
    "https://vote.gov/",
    "https://www.nasa.gov/",
    "https://www.deere.com/en/index.html",
    "https://arxiv.org/list/astro-ph/2301",
    "https://www.cs.cmu.edu/~rwh/",
    "https://pymupdf.readthedocs.io/en/latest/page.html#Page.first_link",
    # Google Sheets
    "https://docs.google.com/spreadsheets/d/1H7_krp7MRSe3u6KHjH1WxuufCm1G-u3xXC01FoZpnMA/",
    "https://docs.google.com/spreadsheets/d/1UviHFPKtf7eHMjN6UweSNWUSDp6KNLH9xJjM6M81j70/",
    "https://docs.google.com/spreadsheets/d/1Dgw-ATH58VK59D7XmprSXigrxZ5faoIpJQ6zeZ00vk8",
    "https://docs.google.com/spreadsheets/d/1GOO4s1NcxCR8a44F0XnsErz5rYDxNbHAHznu4pJMRkw/",
    # pdfs
    "https://github.com/renebidart/papers/raw/master/straussian_moment.pdf",
    "https://arxiv.org/pdf/2110.01485.pdf",
    "https://arxiv.org/pdf/1810.04805.pdf",
    "https://arxiv.org/pdf/2109.13612.pdf",
    "https://arxiv.org/pdf/1904.00739.pdf",
    "https://arxiv.org/pdf/2301.04797.pdf",
    "https://arxiv.org/abs/2301.04874",
    "http://www.cs.uni.edu/~mccormic/4740/guide-c2ada.pdf",
    "https://shreyjoshi.com/AndroidNotesForProfessionals.pdf",
    "https://www.adacore.com/uploads/books/pdf/Ada_for_the_C_or_Java_Developer-cc.pdf",
    "https://www.cs.cmu.edu/~rwh/theses/okasaki.pdf",
]


def crawl():
    response = client.post("/analyze-many", json={
        "urls": initial_urls,
        "recursive_mode": "BFS",
        "maintain_domain": False,
        "max_urls": 15,
        "save_to_azure": True,
        "azure_container_name": "testing",
    })
    assert response.status_code == 200
    # for url, result in response.json().items():
    #     print(url + ": " + str(result))


if __name__ == "__main__":
    with stub.run():
        crawl()
