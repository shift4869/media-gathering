import enum
from dataclasses import dataclass


@dataclass(frozen=True)
class MSG(enum.Enum):
    HORIZONTAL_LINE = "-" * 80
    APPLICATION_START = "Media Gathering -> start"
    APPLICATION_DONE = "Media Gathering -> done"
    APPLICATION_MULTIPLE_RUN = "Media Gathering is now running. This instance is not start."

    CRAWLER_INIT_START = "Crawler init -> start"
    CRAWLER_INIT_DONE = "Crawler init -> done"

    FAVCRAWLER_INIT_START = "Fav Crawler init -> start"
    FAVCRAWLER_INIT_DONE = "Fav Crawler init -> done"
    FAVCRAWLER_MODE = "TAC use mode..."
    FAVCRAWLER_CRAWL_START = "Fav Crawler crawl -> start"
    FAVCRAWLER_CRAWL_DONE = "Fav Crawler crawl -> done"

    RTCRAWLER_INIT_START = "Retweet Crawler init -> start"
    RTCRAWLER_INIT_DONE = "Retweet Crawler init -> done"
    RTCRAWLER_MODE = "TP use mode..."
    RTCRAWLER_CRAWL_START = "Retweet Crawler crawl -> start"
    RTCRAWLER_CRAWL_DONE = "Retweet Crawler crawl -> done"

    LINKSEARCHER_CREATE_START = "LinkSearcher each fetcher registering -> start"
    LINKSEARCHER_CREATE_DONE = "LinkSearcher each fetcher registering -> done"
    LINKSEARCHER_REGISTERED = "LinkSearcher {} -> registered."
    LINKSEARCHER_FETCHER_FOUND = "{} -> Fetcher found: {}."

    MEDIA_DOWNLOAD_START = "Media download -> start"
    MEDIA_DOWNLOAD_DONE = "Media download -> done"

    GETTING_EXTERNAL_LINK_START = "Getting external link -> start"
    GETTING_EXTERNAL_LINK_DONE = "Getting external link -> done"
