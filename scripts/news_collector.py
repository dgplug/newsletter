import os
import sys
import re
import argparse
import json
import feedparser
import dateutil.parser as parser
import datetime
import pprint
import requests
import urllib.parse
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


def get_github_issue_links(source="https://github.com/dgplug/newsletter", newer_than=None):
    response = requests.get(source)
    soup = BeautifulSoup(response.text, 'lxml')
    # issue_count = int(
    #     soup.find('a', {'href': '/dgplug/newsletter/issues'})\
    #         .find('span', {'class': 'Counter'}).text
    # )
    # the above solution is dependent on dgplug/newsletter url
    issue_count = int(
        soup.find('nav', {'class': 'reponav'})(
            text=re.compile(r'Issues')
        )[0].parent.parent.find(
            'span', {'class': "Counter"}
        ).text
    )

    links = []
    for i in range(1, issue_count + 1):
        url = source + '/issues/{}'.format(i)
        html = requests.get(url)
        soup = BeautifulSoup(html.text, 'lxml')
        title = soup.find('span', attrs={'class': 'js-issue-title'}).text
        try:
            date = parser.parse(title.split('release')[-1]).date()
            if date < newer_than:
                continue
        except Exception as e:
            continue

        comments = soup.find_all('div', {'class': 'comment'})
        for comment in comments:
            author = comment.find('a', {'class':'author'}).text
            date = parser.parse(
                comment.find('relative-time').get('datetime')
            ).date()
            comment_links = comment.find('td', {'class': 'comment-body'}).find_all('a')
            for comment_link in comment_links:
                links.append(
                    {
                        'title': comment_link.get('href'),
                        'author': author,
                        'date': date,
                        'link': comment_link.get('href')
                    }
                )

    return links


def main(args):
    two_weeks = datetime.date.today() - datetime.timedelta(weeks=2)
    path = os.path.dirname(__file__)
    resources = json.load(open(os.path.join(path, 'resources.json'), 'r'))

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

    summaries['github_comments'] = get_github_issue_links(
        newer_than=two_weeks
    )

    args.print(args.output, summaries)


def print_json(output, summary):
    json.dump(
        summary,
        open(output, 'w')
    )

def print_markdown(output, summary):
    with open(output, 'w') as outstream:
        for source, contents in summary.items():
            if contents:
                for item in contents:
                    outstream.write(
                        "[{} - {}]({})\n".format(
                            item['author'],
                            item['title'],
                            item['link']
                        )
                    )


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Collect some news from selected resources"
    )
    arg_parser.add_argument(
        'output',
        help="Destination to print the output"
    )
    arg_parser.add_argument(
        '--markdown',
        dest='print',
        action='store_const',
        const=print_markdown,
        default=print_json,
        help="print the results in markdown format (default: json)"
    )
    args = arg_parser.parse_args()

    main(args)
