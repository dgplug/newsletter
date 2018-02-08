
import json
import feedparser
import dateutil.parser as parser
import datetime


def get_rss_feeds(source, newer_than=None):
    entries = feedparser.parse(source).entries
    if newer_than:
        entries = [entry for entry in entries\
                   if parser.parse(entry.updated).date() > newer_than]

    entry_summary = [
        {
            'title': entry.get('title', 'None'),
            'author': entry.get('author', 'unknown'),
            'updated': entry.updated,
            'link': entry.link
        }
        for entry in entries
    ]
    return entry_summary


def main():
    two_weeks = datetime.date.today() - datetime.timedelta(weeks=2)
    resources = json.load(open('resources.json', 'r'))

    summaries = {}
    for rss_source in resources['rss'].values():
        summaries[rss_source['name']] = get_rss_feeds(
            rss_source['url'],
            newer_than=two_weeks
        )


if __name__ == "__main__":
    main()
