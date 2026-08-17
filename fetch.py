#!/usr/bin/env python3
from email.utils import format_datetime as datetime_to_rfc2822
from urllib.request import Request, urlopen
from xml.etree import ElementTree as etree
from typing import Dict, Any, Optional
from argparse import ArgumentParser
from urllib.parse import urlencode
from urllib.error import HTTPError
from datetime import datetime, UTC
from pathlib import Path
from time import sleep
import tomllib
import logging
import enum
import sys

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
        with open(Path(__file__).parent / 'config.toml', 'rb') as f:
            config = tomllib.load(f)
    except FileNotFoundError:
        logging.critical('config.toml not found, aborting.')

        sys.exit(1)

    config['output_dir'] = Path(config.get('output_dir', 'public'))

    if not config['output_dir'].is_absolute():
        config['output_dir'] = (Path(__file__).parent / config['output_dir']).resolve()

    defaults = {
        'filter': config.get('defaults', {}).get('filter', 'submitted'),
        'sort': config.get('defaults', {}).get('sort', 'best'),
        'top_interval': config.get('defaults', {}).get('top_interval', 'day'),
    }

    for sub_name, sub_parameters in config.get('subs', {}).items():
        try:
            sub_parameters['sort'] = Sort(sub_parameters.get('sort', defaults.get('sort')))

            if not sub_parameters['sort'].valid_for_sub():
                raise ValueError
        except ValueError:
            logging.error(f'{sub_name}: invalid "sort" value, this sub will be ignored')

            del config['subs'][sub_name]

            continue

        try:
            sub_parameters['top_interval'] = TopInterval(
                sub_parameters.get('top_interval', defaults.get('top_interval'))
            )
        except ValueError:
            logging.error(f'{sub_name}: invalid "top_interval" value, this sub will be ignored')

            del config['subs'][sub_name]

            continue

    for user_name, user_parameters in config.get('users', {}).items():
        try:
            user_parameters['filter'] = UserFilter(user_parameters.get('filter', defaults.get('filter')))
        except ValueError:
            logging.error(f'{user_name}: invalid "filter" value, this user will be ignored')

            del config['users'][user_name]

            continue

        try:
            user_parameters['sort'] = Sort(user_parameters.get('sort', defaults.get('sort')))

            if not user_parameters['sort'].valid_for_user():
                raise ValueError
        except ValueError:
            logging.error(f'{user_name}: invalid "sort" value, this user will be ignored')

            del config['users'][user_name]

            continue

        try:
            user_parameters['top_interval'] = TopInterval(
                user_parameters.get('top_interval', defaults.get('top_interval'))
            )
        except ValueError:
            logging.error(f'{user_name}: invalid "top_interval" value, this user will be ignored')

            del config['users'][user_name]

            continue

    for domain_name, domain_parameters in config.get('domains', {}).items():
        try:
            domain_parameters['sort'] = Sort(domain_parameters.get('sort', defaults.get('sort')))

            if not domain_parameters['sort'].valid_for_domain():
                raise ValueError
        except ValueError:
            logging.error(f'{domain_name}: invalid "sort" value, this domain will be ignored')

            del config['domains'][domain_name]

            continue

        try:
            domain_parameters['top_interval'] = TopInterval(
                domain_parameters.get('top_interval', defaults.get('top_interval'))
            )
        except ValueError:
            logging.error(f'{domain_name}: invalid "top_interval" value, this domain will be ignored')

            del config['domains'][domain_name]

            continue

    return config


def fetch_feeds(config: Dict[str, Any]) -> None:
    logging.info('Fetching feeds...')

    fetch_subs_feed(config.get('subs', {}), config.get('output_dir'))
    fetch_users_feed(config.get('users', {}), config.get('output_dir'))
    fetch_domains_feed(config.get('domains', {}), config.get('output_dir'))

    logging.info('Done.')


def fetch_subs_feed(subs_config: Dict[str, Any], output_dir: Path) -> None:
    if not subs_config:
        return

    logging.info('Subs...')

    for sub_name, sub_parameters in subs_config.items():
        sort = sub_parameters['sort']
        top_interval = sub_parameters['top_interval']

        download_feed(
            f'r/{sub_name}/{sort}',
            output_dir / 'subs' / f'{sub_name}.atom',
            {'t': str(top_interval)} if sort == Sort.Top else None
        )


def fetch_users_feed(users_config: Dict[str, Any], output_dir: Path) -> None:
    if not users_config:
        return

    logging.info('Users...')

    for user_name, user_parameters in users_config.items():
        filter_ = user_parameters['filter']
        sort = user_parameters['sort']
        top_interval = user_parameters['top_interval']

        query = {
            'sort': sort,
            't': str(top_interval) if sort == Sort.Top else None
        }

        download_feed(
            f'user/{user_name}/{filter_}',
            output_dir / 'users' / f'{user_name}.atom',
            query
        )


def fetch_domains_feed(domains_config: Dict[str, Any], output_dir: Path) -> None:
    if not domains_config:
        return

    logging.info('Domains...')

    for domain_name, domain_parameters in domains_config.items():
        sort = domain_parameters['sort']
        top_interval = domain_parameters['top_interval']

        download_feed(
            f'domains/{domain_name}/{sort}',
            output_dir / 'domains' / f'{domain_name}.atom',
            {'t': str(top_interval)} if sort == Sort.Top else None
        )


def download_feed(path: str, destination: Path, query: Optional[Dict[str, Any]] = None) -> None:
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
        if e.status == 429:
            logging.critical('Got rate-limited anyway, aborting dammit.')

            sys.exit(1)
        else:
            logging.error(e)

    logging.info('Sleeping for 60 seconds (sigh)...')

    try:
        sleep(60)  # Poor's man rate-limiter
    except KeyboardInterrupt:
        logging.critical('Aborted')

        sys.exit(1)


def generate_opml(config: Dict[str, Any]) -> None:
    logging.info('Generating OPML...')

    root = etree.Element('opml', version='2.0')
    head = etree.SubElement(root, 'head')

    etree.SubElement(head, 'title').text = 'Reddit feeds'
    etree.SubElement(head, 'dateCreated').text = datetime_to_rfc2822(datetime.now(tz=UTC))
    etree.SubElement(head, 'docs').text = 'http://opml.org/spec2.opml'

    body = etree.SubElement(root, 'body')

    root_url = config.get('root_url', '').rstrip('/')
    output_dir = config.get('output_dir')

    output_dir.mkdir(parents=True, exist_ok=True)

    generate_subs_opml(body, root_url, config.get('subs', {}))
    generate_users_opml(body, root_url, config.get('users', {}))
    generate_domains_opml(body, root_url, config.get('domains', {}))

    with open(output_dir / 'feeds.opml', 'wb') as f:
        etree.ElementTree(root).write(
            f,
            encoding='utf-8',
            xml_declaration=True
        )

    logging.info('Done.')


def generate_subs_opml(body: etree.Element, root_url: str, subs_config: Dict[str, Any]) -> None:
    if not subs_config:
        return

    logging.info('Subs...')

    subs = etree.SubElement(body, 'outline')
    subs.set('text', 'Subs')

    for sub_name, sub_parameters in subs_config.items():
        sort = sub_parameters['sort']
        top_interval = sub_parameters['top_interval']

        sub = etree.SubElement(subs, 'outline')

        htmlUrl = f'https://www.reddit.com/r/{sub_name}/{sort}/'

        if sort == Sort.Top:
            query = {'t': str(top_interval)}

            htmlUrl += f'?{urlencode(query)}'

        sub.set('text', f'r/{sub_name}')
        sub.set('title', f'r/{sub_name}')
        sub.set('type', 'atom')
        sub.set('xmlUrl', f'{root_url}/subs/{sub_name}.atom')
        sub.set('htmlUrl', htmlUrl)


def generate_users_opml(body: etree.Element, root_url: str, users_config: Dict[str, Any]) -> None:
    if not users_config:
        return

    logging.info('Users...')

    users = etree.SubElement(body, 'outline')
    users.set('text', 'Users')

    for user_name, user_parameters in users_config.items():
        filter_ = user_parameters['filter']
        sort = user_parameters['sort']
        top_interval = user_parameters['top_interval']

        user = etree.SubElement(users, 'outline')

        user.set('text', f'u/{user_name}')
        user.set('title', f'u/{user_name}')
        user.set('type', 'atom')
        user.set('xmlUrl', f'{root_url}/users/{user_name}.atom')

        query = {
            'sort': sort,
            't': str(top_interval) if sort == Sort.Top else None
        }

        user.set('htmlUrl', f'https://www.reddit.com/user/{user_name}/{filter_}/?{urlencode(query)}')


def generate_domains_opml(body: etree.Element, root_url: str, domains_config: Dict[str, Any]) -> None:
    if not domains_config:
        return

    logging.info('Domains...')

    domains = etree.SubElement(body, 'outline')
    domains.set('text', 'Domains')

    for domain_name, domain_parameters in domains_config.items():
        sort = domain_parameters['sort']
        top_interval = domain_parameters['top_interval']

        sub = etree.SubElement(domains, 'outline')

        htmlUrl = f'https://www.reddit.com/domains/{domain_name}/{sort}/'

        if sort == Sort.Top:
            query = {'t': str(top_interval)}

            htmlUrl += f'?{urlencode(query)}'

        sub.set('text', f'domain/{domain_name}')
        sub.set('title', f'domain/{domain_name}')
        sub.set('type', 'atom')
        sub.set('xmlUrl', f'{root_url}/domains/{domain_name}.atom')
        sub.set('htmlUrl', htmlUrl)


def run() -> None:
    arg_parser = ArgumentParser(
        description='Python script to fetch various Reddit feeds in respect to their ridiculous rate limit'
    )

    arg_parser.add_argument(
        '-o', '--opml',
        help='Output OPML file instead of fetching feeds',
        action='store_true'
    )

    args = arg_parser.parse_args()

    config = load_config()

    if args.opml:
        generate_opml(config)
    else:
        fetch_feeds(config)


if __name__ == '__main__':
    run()
