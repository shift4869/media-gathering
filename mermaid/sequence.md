```mermaid
sequenceDiagram
    autonumber

    actor User
    participant media_gathering.py
    participant crawler as FavCrawler.py\<br/>RetweetCrawler.py
    participant fetcher as LikeFetcher.py\<br/>RetweetFetcher.py
    participant LinkSearcher.py
    participant db as FavDBController.py\<br/>RetweetDBController.py
    participant parser as LikeParser.py\<br/>RetweetParser.py
    participant TwitterAPIClientAdapter.py

    box DarkBlue External Library
    participant twitter-api-client
    end

    box DarkGreen External Network
    participant twitter
    participant website
    end

    User ->> media_gathering.py: python media_gathering.py --type="Fav/RT"
    media_gathering.py ->> crawler : make instance, and call

    crawler ->> LinkSearcher.py: make instance
    LinkSearcher.py ->> LinkSearcher.py: init, register ***Fetcher
    LinkSearcher.py ->> crawler: return instance

    crawler ->> db: make instance
    db ->> db: init
    db ->> crawler: return instance

    crawler ->> fetcher: crawl() start
    fetcher ->> TwitterAPIClientAdapter.py: fetch call
    TwitterAPIClientAdapter.py ->> twitter-api-client: fetch call
    twitter-api-client ->> twitter: fetch
    twitter ->> twitter-api-client: fetched data
    twitter-api-client ->> TwitterAPIClientAdapter.py: fetched data
    TwitterAPIClientAdapter.py ->> fetcher: fetched data

    fetcher ->> parser: parse call
    parser ->> fetcher: parse_to_TweetInfo()
    fetcher ->> crawler: fetch call
    crawler ->> twitter: interpret_tweets(), fetch media file
    twitter ->> crawler: media file binary
    crawler -->> User: save media file
    crawler ->> fetcher: return 

    fetcher ->> parser: parse call
    parser ->> fetcher: parse_to_ExternalLink()
    fetcher ->> crawler: trace call
    crawler ->> LinkSearcher.py: trace_external_link()
    LinkSearcher.py ->> website: fetch ExternalLink
    website ->> LinkSearcher.py: media file binary from ExternalLink
    LinkSearcher.py -->> User: save media file
    LinkSearcher.py ->> fetcher: return 

    fetcher ->> crawler: do end_of_process()
    crawler ->> media_gathering.py: return
    media_gathering.py ->> User: return
```