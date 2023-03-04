from urllib3.util import parse_url
import newspaper
from .utils import BasePlugin


class RedditPlugin(BasePlugin):
    def __init__(self):
        self.name = "reddit"
        self.supported_domains = [
            "reddit.com",
            "old.reddit.com",
        ]

    def process(self, url) -> dict:
        """Process Reddit.

        This process function will summarize:
           - Reddit Subreddit Posts
           - Reddit Post Comments
           - Reddit User Comments

        Args:
            url: The url to process.
        """
        # if path is a reddit subreddit, get the top posts
        if "/r/" in url:
            feed = newspaper.build(url, memoize_articles=False)
            feed.download_articles()
            feed.parse_articles()
            titles = [article.title for article in feed.articles]

            # Summary prompt prepends "title_n" to each title
            content = "\n".join(
                [f"article_{i + 1}: {title}" for i, title in enumerate(titles)]
            )
            summary_prompt = content + "\n\nSummarize the previous articles"

            summary = self.summarizer(summary_prompt)

            # summarize the summaries
            return {"content": content, "summary": summary, "raw_source": content}

        # if path is a reddit post, get the comments
        elif "/comments/" in url:
            pass

        # if path is a reddit user, get the comments
        elif "/user/" in url:
            pass
