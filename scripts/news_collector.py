import json
import feedparser
import dateutil.parser as parser
import datetime
import pprint
import requests
from bs4 import BeautifulSoup


def get_rss_feeds(source, newer_than=None):
    entries = feedparser.parse(source).entries
    if newer_than:
        entries = [entry for entry in entries
                   if parser.parse(entry.updated).date() > newer_than]

    entry_summary = [
        {
            'title': entry.get('title', 'None'),
            'author': entry.get('author', 'unknown'),
            'date': entry.updated,
            'link': entry.link
        }
        for entry in entries
    ]
    return entry_summary


def get_twitterlist_tweets(source, newer_than=None):
    response = requests.get(source, headers={"Accept-Language": "en-US"})
    soup = BeautifulSoup(response.text, 'lxml')
    tweets = soup.find_all('li', attrs={"data-item-type": "tweet"})

    if newer_than:
        tweets = [
            tweet for tweet in tweets
            if parser.parse(
                tweet.find('a', attrs={"class": "tweet-timestamp"}).text
            ).date() > newer_than
        ]

    tweet_summary = [
        {
            'title': tweet.find('p', attrs={'class': 'tweet-text'}).text,
            'author': tweet.find('span', attrs={'class': 'username'}).text,
            'date': parser.parse(
                tweet.find('a', attrs={'class': 'tweet-timestamp'}).text
            ).date(),
            'link': "https://twitter.com" +
            tweet.find('a', attrs={'class': 'tweet-timestamp'}).get('href')
        }
        for tweet in tweets
    ]
    return tweet_summary


def main():
    two_weeks = datetime.date.today() - datetime.timedelta(weeks=2)
    resources = json.load(open('resources.json', 'r'))

    summaries = {}
    for rss_source in resources['rss']:
        summaries[rss_source['name']] = get_rss_feeds(
            rss_source['url'],
            newer_than=two_weeks
        )

    for twitter_source in resources['twitter']:
        summaries[twitter_source['name']] = get_twitterlist_tweets(
            twitter_source['url'],
            newer_than=two_weeks
        )

    pprint.pprint(summaries)


if __name__ == "__main__":
    main()
