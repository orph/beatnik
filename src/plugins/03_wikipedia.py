import wikipedia
from .utils import BasePlugin


class WikipediaPlugin(BasePlugin):
    def __init__(self):
        self.name = "wikipedia"
        self.supported_domains = ["wikipedia.com", "en.wikipedia.org", "wikipedia.org"]

    def process(self, url) -> dict:
        """Process Wikipedia.

        This process function will summarize:
           - Wikipedia Page Content

        Args:
            url: The url to process.
        """

        # Get the page title
        page_title = url.split("/")[-1]

        # Get the page summary
        try:
            page_summary = wikipedia.summary(page_title)

            return {"summary": page_summary}
        except Exception as e:
            print(e)
            return {"summary": "No summary found."}

    def get_links(self, url) -> list:
        """Get links from the given URL.

        Args:
            url: The url to process.

        Returns:
            A list of links.
        """
        # Get the page title
        page_title = url.split("/")[-1]

        # Get the page links
        try:
            page_links = wikipedia.page(page_title).links
            page_links = [
                f"https://en.wikipedia.org/wiki/{link}" for link in page_links
            ]
        except Exception as e:
            print(e)
            page_links = []

        return page_links
