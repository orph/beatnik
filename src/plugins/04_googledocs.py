import requests
import re
from .utils import BasePlugin
from urllib3.util import parse_url
import fitz


class GoogledocsPlugin(BasePlugin):
    def __init__(self):
        self.name = "googledocs"
        self.supported_domains = ["docs.google.com"]

    def process(self, url) -> dict:
        """Process Google Sheets.

        This process function will summarize:
           - Google Sheets file

        Args:
            url: The url to process.
        """
        split_url = url.split("/")
        doc_id = split_url[split_url.index("d") + 1]

        # TODO: add support for docs and presentations
        path = parse_url(url).path
        if path.startswith("/spreadsheets/d/"):
            return self.process_sheets(url)
        elif path.startswith("/document/d/"):
            return {"summary": "No summary found. Docs not supported yet."}
        elif path.startswith("/presentation/d/"):
            return {"summary": "No summary found. Presentations not supported yet."}

    # TODO: use google sheets api to access formula instead of just value
    def process_sheets(self, url):
        try:
            csv_request = self.get_sheets_csv(url)
        except Exception as e:
            print(e)
            return {"summary": "No summary found."}

        if 'href="https://accounts.google.com/v3/signin/"' in csv_request.text:
            return {"summary": "Unauthorized to access google sheets."}

        # Get the page summary
        return {"summary": csv_request.text, "raw_source": csv_request.text}

    def get_links(self, url) -> list:
        """Get links from the given URL.

        Args:
            url: The url to process.

        Returns:
            A list of links.
        """
        # very hacky solution for now but works well, maybe try using google sheets api later? rate limiting though
        # pdf parsing currently broken, will fix soon
        url_regex = "(https?://\S+)"
        csv_links = []

        # get sheet as csv to grab all text from cell values
        try:
            csv_text = self.get_sheets_csv(url).text
            for cell in csv_text.split(","):
                csv_links.extend(re.findall(url_regex, cell))
        except Exception as e:
            print(e)

        # and also download as a pdf --> get links embedded in formulas
        # download document
        split_url = url.split("/")
        doc_id = split_url[split_url.index("d") + 1]
        r = requests.get(
            f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=pdf"
        )
        filename = "file.pdf"
        open(filename, "wb+").write(r.content)

        # extract links from document using pymupdf
        pdf_links = []
        try:
            pdf = fitz.open(filename)
            for page in pdf:
                link = page.first_link
                while link:
                    pdf_links.append(link.uri)
                    link = link.next
        except Exception as e:
            print(e)

        # return union of both methods
        return set(csv_links) or set(pdf_links)

    def get_sheets_csv(self, url):
        # Get the DOCID from the url
        split_url = url.split("/")
        doc_id = split_url[split_url.index("d") + 1]

        # Get the csv
        request_url = (
            f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
        )
        return requests.get(request_url)
