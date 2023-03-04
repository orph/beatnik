# Beatnik.AI

Anything-to-text API. Plugins handle specific domains or file extensions, with a fallback to text extraction.

To return summary of text using text-davinci-003, set OPENAI_API_KEY.
To store results in an Azure blob storage container, set CONNECTION_STRING.


## Installation

Install local

```bash
  cd src/
  pip install -r requirements.txt
  playwright install chromium
```

## Usage/Examples

```bash
  python main.py
```


## Deployment

To deploy this project run `modal deploy main.py`.

