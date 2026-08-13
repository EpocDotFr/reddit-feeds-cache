# Reddit feeds cache

We're all tired of Reddit's enshittification. Every month, Reddit is increasingly turning into a data silo, just like
Twitter, Facebook or Digg before it. One day, not a single byte of data will be able to quit Reddit without any form of
authentication. For us open data lovers, Atom feeds are still provided — for now, although these have been severely
rate-limited since June 2026 (one request per minute. Yes, *PER MINUTE*).

So I created this simple script. I want to keep getting updates on things I find interesting without having to visit
Reddit every day — all while staying within their ridiculous rate limit. I do not want to create an account; I do not
want to undergo their ads, nor their new design (yes, there's still old.reddit.com, but its days also are numbered).

## Prerequisites

  - Python >= 3.11
  - A web server

## Installation

Clone this repo somewhere.

Also, you could download `fetch.py` only if you do not want to bother with Git since everything is self-contained in
that script (look ma, no dependencies!).

## Configuration

### This script

Configuration happens through the `config.toml` file, which **must** be located next to `fetch.py`. You will find an
example configuration file (`config.example.toml`) to start with, everything is explained there.

### The web server

Your web server (or its virtual host) must point its root directory to the `public` folder which is automatically created
next to `fetch.py`. Make sure it correctly serve Atom (`*.atom`) and OPML (`*.opml`) files with proper MIME types.

## Usage

### Fetching feeds

This project consists of one Python script, `fetch.py`, which should be invoked at a regular interval (typically using a
job scheduler like cron). It will download and save each configured feed into the `public` folder, while respecting the
rate limit.

For example, fetch feeds every two hours:

```
0 */2 * * * ./path/to/fetch.py
```

Of course, don't run the scheduled job at short intervals: remember it'll take *one whole minute* to download *each*
feed. So given you want to subscribe to 15 feeds, that will take a whopping 15 minutes.

### Subscribing to feeds

You can then subscribe to these feeds using your usual feed reader. They are saved using the following path patterns
(remember it's served from the `public` folder):

  - Subs: `https://your.site/subs/{name}.atom`
  - Users: `https://your.site/users/{username}.atom`
  - Domains: `https://your.site/domains/{domain name}.atom`


### Generate OPML file

You can generate an OPML file so you can subscribe to all of the feeds at once: `./fetch.py --opml`. It's saved in
`public/feeds.opml`.