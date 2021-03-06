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


def get_github_issue_links(
        source="https://github.com/dgplug/newsletter",
        newer_than=None,
        issue=None):
    response = requests.get(source)
    soup = BeautifulSoup(response.text, 'lxml')
    # issue_count = int(
    #     soup.find('a', {'href': '/dgplug/newsletter/issues'})\
    #         .find('span', {'class': 'Counter'}).text
    # )
    # the above solution is dependent on dgplug/newsletter url

    links = []
    issue_count = 1
    while True:
        url = source + '/issues/{}'.format(issue_count)
        html = requests.get(url)
        if html.status_code != 200:
            break
        issue_count += 1
        soup = BeautifulSoup(html.text, 'lxml')
        title = soup.find('span', attrs={'class': 'js-issue-title'}).text

        skip = True

        if skip and issue is not None:
            print("searching {} for issue {}".format(title, issue)) 
            match = re.search(r'.*#([0-9]+).*', title)
            if match is not None:
                try:
                    print('found {}'.format(match.groups()))
                    if int(match.groups()[0]) == int(issue):
                        skip = False
                except Exception as e:
                    print(e)
                    pass

        if skip and newer_than is not None:
            try:
                date = parser.parse(title.split('release')[-1]).date()
                if date >= newer_than:
                    skip = False
            except Exception as e:
                pass
                    
        if skip:
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


def main(args, **kwargs):
    if args.date:
        try:
            two_weeks = parser.parse(args.date).date()
        except:
            print('could not parse date {}'.format(args.date))
            sys.exit(0)
    else:
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
        newer_than=two_weeks,
        issue=args.issue
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
            for idx, item in enumerate(contents):
                outstream.write(
                    "[{} - {}][{}_{}]\n".format(
                        item['author'],
                        item['title'],
                        source,
                        idx
                    )
                )
                outstream.write(
                    "[{}_{}]: {}\n".format(
                        source,
                        idx,
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
    arg_parser.add_argument(
        '--newer-than',
        dest='date',
        help="set date of the oldest content that should be included (default: 2 weeks before today)"
    )
    arg_parser.add_argument(
        '--github-issue',
        dest='issue',
        help="specify a github issue to be included in the search"
    )
    args = arg_parser.parse_args()

    main(args)
