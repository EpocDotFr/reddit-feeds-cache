# Reddit feeds cache

We're all tired of Reddit's enshittification. Every month, Reddit is increasingly turning into a data silo, just like
Twitter, Facebook or Digg before it. One day, not a single byte of data will be able to quit Reddit without any form of
authentication. For us open data lovers, Atom feeds are still provided — for now, although these have been severely
rate-limited since June 2026 (one request per minute. Yes, *PER MINUTE*).

So I created this simple script. I want to keep getting updates on things I find interesting without having to visit
Reddit every day — all while staying within their ridiculous rate limit. I do not want to create an account; I do not want to
undergo their ads, nor their new design (yes, there's still old.reddit.com, but its days also are numbered).

## Prerequisites

  - Python >= 3.11
  - A web server

## Installation

Clone this repo somewhere.

Also, you could download `fetch.py` only if you do not want to bother with Git since everything is self-contained in
that script (look ma, no dependencies!).

## Configuration

Configuration happens through the `config.toml` file, which **must** be located next to `fetch.py`. You will find an
example configuration file (`config.example.toml`) to start with, everything is explained there.

Your web server (or its virtual host) must point its root directory to the `public` folder which is automatically created
next to `fetch.py`. Make sure it correctly serve Atom (`*.atom`) files with proper MIME types.

## Usage

This project consists of one Python script, `fetch.py`, which should be invoked at a regular interval (typically using a
job scheduler like cron). It will download and save each configured feed into the `public` folder, while respecting the
rate limit.

For example, fetch feeds every two hours:

```
0 */2 * * * cd /path/to/the/script && ./fetch.py
```

You can then subscribe to these feeds using your usual feed reader. They are saved using the following path patterns:

  - Subs: `https://your.site/subs/{name}.atom`
  - Users: `https://your.site/users/{username}.atom`
  - Domains: `https://your.site/domains/{domain name}.atom`

Plain old static files: that's all we need.

## TODO

  - [ ] Allow to define default `sort`, `top_interval` and `filter` values
