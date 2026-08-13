#!/usr/bin/env python3
from urllib.request import Request, urlopen
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from urllib.error import HTTPError
from pathlib import Path
from time import sleep
import tomllib
import logging
import enum

logging.basicConfig(level=logging.INFO)


@enum.unique
class Sort(enum.StrEnum):
    Best = 'best'
    Hot = 'hot'
    New = 'new'
    Top = 'top'
    Rising = 'rising'
    Controversial = 'controversial'

    def valid_for_sub(self) -> bool:
        return self in [Sort.Best, Sort.Top, Sort.Hot, Sort.New, Sort.Rising]

    def valid_for_user(self) -> bool:
        return self in [Sort.Top, Sort.Hot, Sort.New]

    def valid_for_domain(self) -> bool:
        return self in [Sort.Hot, Sort.New, Sort.Rising, Sort.Controversial, Sort.Top]


@enum.unique
class TopInterval(enum.StrEnum):
    Hour = 'hour'
    Day = 'day'
    Week = 'week'
    Month = 'month'
    Year = 'year'
    All = 'all'


@enum.unique
class UserFilter(enum.StrEnum):
    Submitted = 'submitted'
    Comments = 'comments'


def load_config() -> Dict[str, Any]:
    logging.info('Loading configuration...')

    try:
        with open(Path(__file__).parent / 'config.example.toml', 'rb') as f:
            return tomllib.load(f)
    except FileNotFoundError:
        logging.critical('config.toml not found, aborting.')

        exit(1)


def fetch_feeds(config: Dict[str, Any]) -> None:
    logging.info('Fetching feeds...')

    defaults = {
        'filter': config.get('defaults', {}).get('filter', 'submitted'),
        'sort': config.get('defaults', {}).get('sort', 'best'),
        'top_interval': config.get('defaults', {}).get('top_interval', 'day'),
    }

    fetch_subs_feed(config.get('subs', {}), defaults)
    fetch_users_feed(config.get('users', {}), defaults)
    fetch_domains_feed(config.get('domains', {}), defaults)

    logging.info('Done.')


def fetch_subs_feed(subs_config: Dict[str, Any], defaults: Dict[str, Any]) -> None:
    if not subs_config:
        return

    logging.info('Subs...')

    for sub_name, sub_parameters in subs_config.items():
        try:
            sort = Sort(sub_parameters.get('sort', defaults.get('sort')))

            if not sort.valid_for_sub():
                raise ValueError
        except ValueError:
            logging.error(f'{sub_name}: invalid "sort" value')

            continue

        try:
            top_interval = TopInterval(sub_parameters.get('top_interval', defaults.get('top_interval')))
        except ValueError:
            logging.error(f'{sub_name}: invalid "top_interval" value')

            continue

        download_feed(
            f'r/{sub_name}/{sort}',
            Path('subs') / f'{sub_name}.atom',
            {'t': str(top_interval)} if sort == Sort.Top else None
        )


def fetch_users_feed(users_config: Dict[str, Any], defaults: Dict[str, Any]) -> None:
    if not users_config:
        return

    logging.info('Users...')

    for user_name, user_parameters in users_config.items():
        try:
            filter_ = UserFilter(user_parameters.get('filter', defaults.get('filter')))
        except ValueError:
            logging.error(f'{user_name}: invalid "filter" value')

            continue

        try:
            sort = Sort(user_parameters.get('sort', defaults.get('sort')))

            if not sort.valid_for_user():
                raise ValueError
        except ValueError:
            logging.error(f'{user_name}: invalid "sort" value')

            continue

        try:
            top_interval = TopInterval(user_parameters.get('top_interval', defaults.get('top_interval')))
        except ValueError:
            logging.error(f'{user_name}: invalid "top_interval" value')

            continue

        download_feed(
            f'user/{user_name}/{filter_}',
            Path('users') / f'{user_name}.atom',
            {'t': str(top_interval)} if sort == Sort.Top else None
        )


def fetch_domains_feed(domains_config: Dict[str, Any], defaults: Dict[str, Any]) -> None:
    if not domains_config:
        return

    logging.info('Domains...')

    for domain_name, domain_parameters in domains_config.items():
        try:
            sort = Sort(domain_parameters.get('sort', defaults.get('sort')))

            if not sort.valid_for_domain():
                raise ValueError
        except ValueError:
            logging.error(f'{domain_name}: invalid "sort" value')

            continue

        try:
            top_interval = TopInterval(domain_parameters.get('top_interval', defaults.get('top_interval')))
        except ValueError:
            logging.error(f'{domain_name}: invalid "top_interval" value')

            continue

        download_feed(
            f'domains/{domain_name}/{sort}',
            Path('domains') / f'{domain_name}.atom',
            {'t': str(top_interval)} if sort == Sort.Top else None
        )


def download_feed(path: str, destination: Path, query: Optional[Dict[str, Any]] = None) -> None:
    destination = Path(__file__).parent / 'public' / destination
    destination.parent.mkdir(parents=True, exist_ok=True)

    url = f'https://www.reddit.com/{path}.rss'

    if query:
        url += f'?{urlencode(query)}'

    logging.info(url)

    request_object = Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0',
        },
        origin_req_host='www.reddit.com',
        method='GET'
    )

    try:
        with urlopen(request_object) as response:
            with open(destination, 'wb') as f:
                f.write(response.read())
    except HTTPError as e:
        logging.error(e)

        if e.status == 429:
            logging.critical('Got rate-limited anyway, aborting dammit.')

            exit(1)
        elif e.status == 404:
            logging.error('Feed not found.')

            return
        elif 'application/atom+xml' not in e.headers.get('Content-Type', ''):
            logging.error('Did not get an Atom file.')

            return

    logging.info('Sleeping for 60 seconds (sigh)...')

    try:
        sleep(60)  # Poor's man rate-limiter
    except KeyboardInterrupt:
        logging.critical('Aborted')

        exit(1)


def run() -> None:
    fetch_feeds(
        load_config()
    )


if __name__ == '__main__':
    run()
