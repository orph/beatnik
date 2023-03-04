"""YoutubePlugin

Plugin for YouTube video analysis

Note:
    Plugin class names are determined by the plugin module name.
    For example, the plugin module name "02_youtube.py" will result in the
    plugin class name "YoutubePlugin".
"""

import time
from urllib3.util import parse_url
from youtube_transcript_api import YouTubeTranscriptApi
from playwright.sync_api import sync_playwright
from parsel import Selector
import json
import re
from .utils import url_to_param_dict, BasePlugin

# youtube paths and params:
# /watch?v=___
# /@name and /channel/xyz for channels
# /playlist?list=___
# /shorts


class YoutubePlugin(BasePlugin):
    def __init__(self):
        self.name = "youtube"
        self.supported_domains = [
            "youtube.com",
            "youtu.be",
        ]
        self.page_source = None

    def get_links(self, url):
        """Gets all urls from the given youtube page with youtube domain

        Args:
            url: The url to process

        Returns:
            links: a list of links"""

        # us playwright to load videos/comments and get all href attributes --> turn it into a urllib obj
        page_source = self.page_source or self.get_page_source(url)
        selector = Selector(page_source)
        links = [url for url in selector.css("a::attr(href)").getall()]

        # create array of link objects with url and params
        links = [
            {
                "url": link,
                # keep hostname if given, else use 'youtube.com'
                "hostname": parse_url(link).hostname.lstrip("www.")
                if parse_url(link).hostname
                else "youtube.com",
                # split path into list if given, else use empty array
                "path": [i for i in parse_url(link).path.split("/") if i != ""]
                if parse_url(link).path
                else [],
                "params": url_to_param_dict(link),
            }
            for link in links
        ]

        # filtering and removing duplicate links:

        # 1) staying on youtube for now
        links = [link for link in links if link["hostname"] == "youtube.com"]
        links = [link for link in links if link["path"] == ["watch"]]

        # 2) only keep necessary parameters for each pathname
        for link in links:
            if "watch" in link["path"]:
                link["params"] = {"v": link["params"]["v"]}
            elif "playlist" in link["path"]:
                link["params"] = {"v": link["params"]["list"]}
            else:
                link["params"] = {}

        # 3) reconstruct url string and return unique urls
        unique_links = set()
        for link in links:
            params = link["params"]
            param_string = ""
            for key in params.keys():
                param_string += f"{key}={params[key]}"
            url = f"https://{link['hostname']}/{'/'.join(link['path'])}{'?' if param_string else ''}{param_string}"
            unique_links.add(url)

        return unique_links

    def get_transcript(self, video_id) -> str:
        transcript = {}
        transcript_text = ""
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id=video_id)
            # transcript is an array of {text: str, start: float, end: float} objects which we parse to get text
            transcript_text: str = " ".join(
                [segment["text"].replace("\n", " ") for segment in transcript]
            )
        except:
            print("Subtitles are not enabled for this video")

        return transcript_text

    def process(self, url) -> dict:
        """Process the given youtube page.

        Args:
            url: The website to process.
        """

        # extract path and parameters from url
        path = parse_url(url).path
        params = url_to_param_dict(url)

        # process page based on path and params

        if path == "/":
            return {"summary": "YouTube homepage."}
        elif path == "/watch":
            return self.process_watch(
                url=url,
                video_id=params["v"],
            )
        elif path == "/playlist":
            return self.process_playlist(playlist_id=params["list"])
        elif path == "/channel" or path[1] == "@":
            return self.process_channel(url)

    def process_watch(self, url: str, video_id: str) -> dict:
        """Process the /watch path for a single video.

        Args:
            video_id (str): The video ID.
        """

        transcript_text = self.get_transcript(video_id)

        # Summarize the first 500 characters of the transcript
        transcript_prompt = (
            transcript_text[:100] + "\n\nSummarize the previous video transcript"
        )
        summary = self.summarizer(transcript_prompt)

        # todo get video title, description, tags, numViews, upload date, numLikes, comment list
        # https://serpapi.com/blog/scrape-youtube-video-page-with-python/

        page_source = self.page_source or self.get_page_source(url)
        data = self.scrape_all_data(page_source)

        return {
            "content": transcript_text,
            "summary": summary,
            "data": data,
            "raw_source": page_source,
        }

    def process_playlist(self, playlist_id: str) -> dict:
        """Process the /playlist path.

        Args:
            playlist_id (str): The playlist ID.
        """

        # todo return videoList of names + videoIDs
        video_list = []
        return {"videoList": video_list}

    def process_channel(self, url: str) -> dict:
        """Process the /channel or /@username paths."""

        summary: str = "Empty"

        return {
            "summary": summary,
        }

    def get_page_source(self, url: str) -> str:
        """Scrolls page to load suggest videos and comments"""
        start = time.time()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.new_context(
                # lang="en",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
            )
            page = browser.new_page()
            page.set_viewport_size(viewport_size={"width": 1366, "height": 768})
            end = time.time()
            print("time to open playwright:", end - start)
            page.goto(url)
            page.wait_for_selector("ytd-app")

            old_height = page.evaluate(
                "() => document.querySelector('ytd-app').scrollHeight"
            )

            # you can change the 5 to any value, this value just keeps request time low
            for i in range(5):
                page.evaluate(
                    "() => window.scrollTo(0, document.querySelector('ytd-app').scrollHeight)"
                )

                time.sleep(2)

                new_height = page.evaluate(
                    "document.querySelector('ytd-app').scrollHeight"
                )

                if new_height == old_height:
                    break

                old_height = new_height

            page_source = page.content()
            browser.close()

        # cache page source to prevent duplicate calls
        self.page_source = page_source
        return page_source

    def scrape_all_data(self, page_source: str):
        selector = Selector(page_source)
        all_script_tags = selector.css("script").getall()

        title = selector.css(".title .ytd-video-primary-info-renderer::text").get()

        date = selector.css("#info-strings yt-formatted-string::text").get()

        duration = selector.css(".ytp-time-duration::text").get()

        # https://regex101.com/r/0JNma3/1
        keywords = (
            "".join(
                re.findall(
                    r'"keywords":\[(.*)\],"channelId":".*"', str(all_script_tags)
                )
            )
            .replace('"', "")
            .split(",")
        )

        # https://regex101.com/r/9VhH1s/1
        thumbnail = re.findall(
            r'\[{"url":"(\S+)","width":\d*,"height":\d*},', str(all_script_tags)
        )[0].split('",')[0]

        channel = {
            # https://regex101.com/r/xFUzq5/1
            "id": "".join(
                re.findall(r'"channelId":"(.*)","isOwnerViewing"', str(all_script_tags))
            ),
            "name": selector.css("#channel-name a::text").get(),
            "link": f'https://www.youtube.com{selector.css("#channel-name a::attr(href)").get()}',
            "subscribers": selector.css("#owner-sub-count::text").get(),
            "thumbnail": selector.css("#img::attr(src)").get(),
        }

        description = selector.css(
            ".ytd-expandable-video-description-body-renderer span:nth-child(1)::text"
        ).get()

        # https://regex101.com/r/onRk9j/1
        category = "".join(
            re.findall(r'"category":"(.*)","publishDate"', str(all_script_tags))
        )

        num_comments = selector.css("#count::text").get()

        comments = []

        for comment in selector.css("#contents > ytd-comment-thread-renderer"):
            comments.append(
                {
                    "author": comment.css("#author-text span::text").get().strip(),
                    "link": f'https://www.youtube.com{comment.css("#author-text::attr(href)").get()}',
                    "date": comment.css(".published-time-text a::text").get(),
                    "likes": comment.css("#vote-count-middle::text").get().strip(),
                    "comment": comment.css("#content-text::text").get(),
                }
            )

        suggested_videos = []

        for video in selector.css("ytd-compact-video-renderer"):

            suggested_videos.append(
                {
                    "title": video.css("#video-title::text").get().strip(),
                    "link": f'https://www.youtube.com{video.css("#thumbnail::attr(href)").get()}',
                    # "channel_name": video.css("#channel-name #text::text").get(),
                    #     "date": video.css("#metadata-line span:nth-child(2)::text").get(),
                    #     "views": video.css("#metadata-line span:nth-child(1)::text").get(),
                    #     "duration": video.css("#overlays #text::text").get().strip(),
                    #     "thumbnail": video.css("#thumbnail img::attr(src)").get(),
                }
            )

        data = {
            "title": title,
            "date": date,
            "duration": duration,
            "channel": channel,
            "keywords": keywords,
            "thumbnail": thumbnail,
            "description": description,
            "category": category,
            "suggested_videos": suggested_videos,
            "num_comments": num_comments,
            "comments": comments,
        }

        return data
