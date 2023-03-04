import importlib
import os
from fastapi import FastAPI
from pydantic import BaseModel
import modal
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import uuid
from datetime import datetime

from urllib3.util import parse_url

image = (
    modal.Image.debian_slim()
    .run_commands(
        "apt-get update",
        "apt-get upgrade -y",
        "apt-get install sudo -y",
        "sudo apt-get install python-dev-is-python3 libxml2-dev libxslt1-dev antiword unrtf poppler-utils tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev swig libpulse-dev -y",
    )
    .pip_install_from_requirements("./requirements.txt")
    .run_commands(
        "python -m nltk.downloader punkt",
        "playwright install-deps",
        "playwright install",
    )
)

stub = modal.Stub("beatnik", image=image)
stub["openai-secret"] = modal.Secret({"OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY")})
stub["azure-beatnik-storage-connection-string"] = modal.Secret({"CONNECTION_STRING": os.environ.get("CONNECTION_STRING")})

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Beatnik A.I."}

class AzureIOManager:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

    def upload_file(self, container_name, file_path, file_name, contents):
        """
        Uploads a file to Azure Blob Storage
        Args:
            container_name: The name of the container to upload to
            file_path: The path to the file. If empty string, file will be uploaded to root of container.
            file_name: The name of the file
            contents: The contents of the file
        Returns:
            None
        """
        container_client = self.blob_service_client.get_container_client(container_name)
        if file_path != "":
            blob_name = file_path + '/' + file_name
        else:
            blob_name = file_name
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(contents)

class BeatnikScraper:
    def __init__(self, plugin_dir, recursive_mode, maintain_domain, max_urls, save_to_azure, azure_container_name=None, azure_file_path=None):
        self.plugin_dir = plugin_dir
        self.available_plugins = {}
        self.load_plugins()
        self.recursive_mode = recursive_mode
        self.maintain_domain = maintain_domain
        self.max_urls = max_urls
        if save_to_azure:
            self.save_to_azure = True
            self.azure_io_manager = AzureIOManager(os.environ.get("CONNECTION_STRING"))
            self.azure_container_name = azure_container_name
            self.azure_file_path = azure_file_path
        else:
            self.save_to_azure = False

    def load_plugins(self):
        # TODO: clean this up - it's quite messy
        for module_name in sorted(os.listdir(self.plugin_dir)):
            if (
                module_name.endswith(".py")
                and "utils" not in module_name
                and "__init__" not in module_name
            ):
                plugin_module = importlib.import_module(f"plugins.{module_name[:-3]}")
                plugin_module_name = module_name[:-3]
                plugin_class_name = plugin_module_name.split("_")[1].capitalize()
                plugin_class = getattr(plugin_module, f"{plugin_class_name}Plugin")
                plugin = plugin_class()
                if plugin_module_name not in self.available_plugins.keys():
                    self.available_plugins[plugin_module_name] = (
                        plugin,
                        plugin.supported_domains,
                    )

    def get_hostname(self, url):
        parsed_url = parse_url(url)
        return parsed_url.hostname.lower().lstrip("www.")

    def get_proper_handler(self, url):
        hostname = self.get_hostname(url)
        for plugin_name, plugin in self.available_plugins.items():
            if hostname in plugin[1]:
                return plugin[0]
        return self.available_plugins["99_default"][0]

    def is_valid_url(self, url):
        parsed_url = parse_url(url)
        if parsed_url.scheme not in ("http", "https"):
            return False
        return True

    def scrape_url(self, url):
        if not self.is_valid_url(url):
            return {}
        else:
            plugin = self.get_proper_handler(url)
            if hasattr(plugin, "setup_credentials"):
                plugin.setup_credentials()
            try:
                results = plugin.process(url)
            except Exception as e:
                print(e)
                results = {}
            return results

    def scrape(self, url):
        starting_domain = parse_url(url).hostname.lower().lstrip("www.")
        results_dict = {}
        if self.recursive_mode == "None":
            scraped = self.scrape_url(url)
            if self.save_to_azure:
                file_name = self.get_hostname(url) + '_' + str(uuid.uuid4()) + '.json'
                self.azure_io_manager.upload_file(self.azure_container_name, self.azure_file_path, file_name, str(scraped))
            results_dict.update(scraped)
            return results_dict
        elif self.recursive_mode == "BFS":
            queue = [url]
            discovered = [url]

            # TODO: clean this up
            while queue and len(results_dict) < self.max_urls:
                url = queue.pop(0)
                if self.is_valid_url(url):
                    scraped = self.scrape_url(url)                        
                    if self.save_to_azure:
                        file_name = self.get_hostname(url) + '_' + str(uuid.uuid4()) + '.json'
                        self.azure_io_manager.upload_file(self.azure_container_name, self.azure_file_path, file_name, str({url: scraped}))
                    results_dict.update({url: scraped})
                    plugin = self.get_proper_handler(url)
                    if hasattr(plugin, "get_links"):
                        urls = plugin.get_links(url)
                        for url in urls:
                            if (
                                url is not None
                                and parse_url(url).hostname is not None
                                and (
                                    (
                                        self.maintain_domain
                                        and self.get_hostname(url)
                                        == starting_domain
                                    )
                                    or self.maintain_domain == False
                                )
                                and url not in discovered
                            ):
                                queue.append(url)
                                discovered.append(url)

            return results_dict


# TODO: It's unclear why we need to mount volumes twice. Can we do it once in the stub definition?
@stub.function(
    mounts=[modal.Mount(local_dir="./plugins", remote_dir="/root/plugins")],
    secrets=[modal.Secret.from_name("openai-secret"), modal.Secret.from_name("azure-beatnik-storage-connection-string")],
)
def scrape_url(url, recursive_mode, maintain_domain, max_urls, save_to_azure, azure_container_name, run_id):
    if save_to_azure:
        azure_file_path = run_id + '/successes'
    else:
        azure_file_path = None

    BS = BeatnikScraper(
        plugin_dir="./plugins",
        recursive_mode=recursive_mode,
        maintain_domain=maintain_domain,
        max_urls=max_urls,
        save_to_azure=save_to_azure,
        azure_container_name=azure_container_name,
        azure_file_path=azure_file_path,
    )
    results = BS.scrape(url)
    return results

class ScrapeRequest(BaseModel):
    url: str
    recursive_mode: str
    maintain_domain: bool
    max_urls: int
    save_to_azure: bool
    azure_container_name: str


@app.post("/analyze")
def analyze(request: ScrapeRequest) -> dict:
    run_id = str(datetime.now()).replace(' ', '_')
    results = scrape_url.call(
        url=request.url,
        recursive_mode=request.recursive_mode,
        maintain_domain=request.maintain_domain,
        max_urls=request.max_urls,
        save_to_azure=request.save_to_azure,
        azure_container_name=request.azure_container_name,
        run_id=run_id,
    )
    return results


class MultiScrapeRequest(BaseModel):
    urls: list
    recursive_mode: str
    maintain_domain: bool
    max_urls: int # in this case, this is the max number of urls per url
    save_to_azure: bool
    azure_container_name: str

@stub.function(
    secrets=[modal.Secret.from_name("openai-secret"), modal.Secret.from_name("azure-beatnik-storage-connection-string")],
)
def save_failure(azure_container_name, file_path, file_name, text):
    FailureIOManager = AzureIOManager(os.environ.get("CONNECTION_STRING"))
    FailureIOManager.upload_file(azure_container_name, file_path, file_name, text)

@app.post("/analyze-many")
def analyze_many(request: MultiScrapeRequest) -> dict:
    run_id = str(datetime.now()).replace(' ', '_')
    results = {}
    for result in scrape_url.map(request.urls, kwargs={
        "recursive_mode": request.recursive_mode,
        "maintain_domain": request.maintain_domain,
        "max_urls": request.max_urls,
        "save_to_azure": request.save_to_azure,
        "azure_container_name": request.azure_container_name,
        "run_id": run_id,
    }, return_exceptions=True):
        if isinstance(result, Exception):
            file_path = run_id + '/failures'
            save_failure.call(azure_container_name=request.azure_container_name, file_path=file_path, file_name=str(uuid.uuid4()) + '.json', text=str(result))
        else:
            results.update(result)
    return results

class UploadRequest(BaseModel):
    container_name: str
    file_path: str
    file_name: str
    contents: str

@stub.function(
    mounts=[modal.Mount(local_dir="./plugins", remote_dir="/root/plugins")],
    secrets=[modal.Secret.from_name("openai-secret"), modal.Secret.from_name("azure-beatnik-storage-connection-string")],
)
def upload_helper(container_name, file_path, file_name, contents):
    AIM = AzureIOManager(connection_string=os.environ.get("CONNECTION_STRING"))
    AIM.upload_file(container_name, file_path, file_name, contents)

@app.post("/test-upload")
def test_upload(request: UploadRequest):
    upload_helper(
        container_name=request.container_name,
        file_path=request.file_path,
        file_name=request.file_name,
        contents=request.contents,
    )

# for testing plugin get_links methods
# TODO: cleanup recursion code and integrate this cleanly
@app.post("/links")
def get_site_links(request: ScrapeRequest) -> dict:
    BS = BeatnikScraper(
        plugin_dir="./plugins",
        recursive_mode=request.recursive_mode,
        maintain_domain=request.maintain_domain,
        max_urls=request.max_urls,
    )
    plugin = BS.get_proper_handler(request.url)
    links = []
    if hasattr(plugin, "get_links"):
        links = plugin.get_links(request.url)
    return {"links": links}

@stub.asgi(
    mounts=[modal.Mount(local_dir="./plugins", remote_dir="/root/plugins")],
    secrets=[modal.Secret.from_name("openai-secret"), modal.Secret.from_name("azure-beatnik-storage-connection-string")],
)
def fastapi_app():
    return app


if __name__ == "__main__":
    stub.serve()
