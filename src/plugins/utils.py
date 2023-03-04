import os
import openai


def url_to_param_dict(url: str) -> dict:
    """Extracts all the parameters after the '?' char in a url into a structured dictionary format.
    All dict values are strings"""

    if "?" not in url:
        return {}

    param_list = url.split("?")[1].split("&")
    param_dict = {}
    for param in param_list:
        key, value = param.split("=")
        param_dict[key] = value
    return param_dict


class BasePlugin:
    def __init__(self):
        self.api_key = None

    def setup_credentials(self):
        """Set up the credentials for the plugin from environment."""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        openai.api_key = self.api_key

    def summarizer(self, prompt: str) -> str:
        """Call LLM to summarize the given prompt.

        Args:
            prompt (str): The prompt to summarize.
        """

        if not self.api_key:
            return ""

        try:
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=prompt,
                temperature=0.0,
                max_tokens=1000,
                top_p=1,
                best_of=3,
                frequency_penalty=0,
                presence_penalty=0,
            )

            return response.to_dict_recursive()["choices"][0]["text"].strip()
        except Exception as e:
            print(e)
            return "error"


document_extensions = {
    "csv",
    "doc",
    "docx",
    "eml",
    "epub",
    "gif",
    "jpg",
    "json",
    "mp3",
    "msg",
    "odt",
    "ogg",
    "pdf",
    "png",
    "pptx",
    "ps",
    "rtf",
    "tiff",
    "txt",
    "wav",
    "xlsx",
    "xls",
}
