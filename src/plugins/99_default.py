"""DefaultPlugin

Plugin for sites that are not supported by any other plugin.

Note:
    Plugin class names are determined by the plugin module name.
    For example, the plugin module name "99_default.py" will result in the
    plugin class name "DefaultPlugin".

Hint:
    This plugin should always be the last plugin in the list of plugins.
"""
from playwright.sync_api import sync_playwright
from .utils import BasePlugin, document_extensions
import textract
import requests
import re
import mimetypes
from newspaper import Article
import fitz

"""
This default plugin should handle most use cases, websites, and file formats

things to fix:
- does not extract text from images inside pdf
- does not describe images, only uses OCR
- CSVs are outputted as TSVs (tab separated format)
- google sheets not handled
- anything with authentication not handled
- website content is bytestring, meaning lots of '\n's and similar quirkiness
"""


def supports_url(url: str) -> bool:
    """Check if the plugin supports the given URL.

    The default plugin supports all URLs.
    """
    return True


class DefaultPlugin(BasePlugin):
    def __init__(self) -> None:
        self.name = "default"
        self.supported_domains = ["*"]
        self.document_extensions = document_extensions
        self.timeout = 5
        self.page_source = None
        self.links = None

    def get_content_type(self, url):
        content_type = None
        try:
            return requests.head(url, timeout=self.timeout).headers.get("content-type")
        except Exception as e:
            print(e)
            return None

    def process(self, url) -> dict:
        print("processing with default plugin:", url)
        content_type = self.get_content_type(url)

        if content_type is None:
            return {"content": "Could not reach webpage in time"}
        # if it's a webpage use playwright to get html and then use textract
        elif "text/html" in content_type:
            print("- using website processing.")
            return self.process_webpage(url)
        # if it's a document filetype, download it and use textract
        else:
            print("- using document processing.")
            return self.process_document(url)

    def process_document(self, url):
        # download document
        r = requests.get(url)
        extension = mimetypes.guess_extension(self.get_content_type(url))
        filename = f"file{extension}"
        if extension is None:
            print(self.get_content_type(url))
            return {"content": "Document extension not supported"}
        if extension.lstrip(".") not in self.document_extensions:
            return {"content": "Document extension not supported"}

        open(filename, "wb+").write(r.content)

        # extract text from document
        try:
            content = textract.process(filename, output_encoding="utf-8").decode(
                "utf-8"
            )
            # remove whitespace
            content = " ".join(content.split())
        except Exception as e:
            print(e)
            content = "Document could not be processed"

        return {
            "content": content,
            "summary": self.summarizer(content),
            "raw_source": content,
        }

    def cache_webpage_data(self, url):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                # cache page source and links
                self.page_source = page.content()
                self.links = page.evaluate(
                    """() => [...document.querySelectorAll('a')].map(link => link.href);"""
                )
                browser.close()
        except Exception as e:
            print(e)
            print("Webpage data could not be cached")

    def process_webpage(self, url):
        # use playwright to open and get html then process
        try:
            self.cache_webpage_data(url)
        except Exception as e:
            print(e)
            return {
                "content": "Webpage data could not be cached",
                "raw_source": None,
            }

        try:
            # process retrieved html
            filename = "file.html"
            open(filename, "w+").write(self.page_source)
            content = textract.process(filename, output_encoding="utf-8")

            # remove whitespace
            content = " ".join(content.decode("utf-8").split())
        except Exception as e:
            print(e)
            return {
                "content": "Webpage data could not be processed",
                "raw_source": None,
            }

        summary = self.summarizer(
            "summarize the following webpage content:\n" + content
        )
        return {"raw_source": self.page_source, "content": content, "summary": summary}

    def get_links(self, url) -> list:
        content_type = self.get_content_type(url)

        if "text/html" in content_type:
            print("- getting webpage links")
            self.links = self.get_webpage_links(url)
        else:
            print("- getting document links")
            self.links = self.get_document_links(url)

        # remove empty urls, fragment identifiers, and mailtos
        links = {
            link
            for link in self.links
            if link != "" and "#" not in link and not link.startswith("mailto:")
        }

        return links

    def get_webpage_links(self, url):
        # cache the links first
        self.cache_webpage_data(url)

        return self.links

    def get_document_links(self, url):
        # download document
        r = requests.get(url)
        extension = mimetypes.guess_extension(self.get_content_type(url))
        
        if extension is None:
            print("can't get links: document type not supported")
            print(self.get_content_type(url))
            return []
        if extension.lstrip(".") not in self.document_extensions:
            print("can't get links: document type not supported")
            return []
        # special processing for pdfs
        elif extension == ".pdf":
            return self.get_pdf_links(url)

        filename = f"file{extension}"
        open(filename, "wb+").write(r.content)

        # extract text from document
        try:
            content = textract.process(filename, output_encoding="utf-8").decode(
                "utf-8"
            )
        except Exception as e:
            print(e)
            content = ""

        # TODO: update regex?
        url_regex = "(https?://\S+)"
        links = re.findall(url_regex, content)
        return links

    def get_pdf_links(self, url):
        # download document
        r = requests.get(url)
        extension = mimetypes.guess_extension(self.get_content_type(url))
        if extension.lstrip(".") not in self.document_extensions:
            print("can't get links: document type not supported")
            return []
        filename = f"file{extension}"
        open(filename, "wb+").write(r.content)

        # extract links from document using pymupdf
        links = []
        try:
            pdf = fitz.open(filename)
            for page in pdf:
                link = page.first_link
                while link:
                    links.append(link.uri)
                    link = link.next
        except Exception as e:
            print(e)

        return links
