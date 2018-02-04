#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Little program to crawl some ToR pages and demonstrate the usage of the Stem API to
connect ToR from within Python.

Made by Foo-Manroot
Last change on Feb 04, 2018
"""

import logging \
    , sys \
    , re \
    , io \
    , pycurl

from urllib.parse import urlparse \
                        , urljoin

# To parse HTML
from bs4 import BeautifulSoup

class Crawler ():
    """
    Spider to extract all links on the provided URL, mapping an entire webpage along
    with the linked webs.

    The process is repeated in every webpage found until no more links are left.
    """

    def __init__ (self, initial_url, proxy_port = None, max_depth = 2):
        """
        Constructor

        Args:
            initial_url -> Starting URL from which the spider will begijn crawling

            proxy_port (OPTIONAL) -> Port where the local proxy is listening on. If it's
                    None, no proxy will be used

            max_depth (OPTIONAL) -> Maximum recursion depth
        """
        self.initial_url = initial_url
        self.max_depth = max_depth

        self.user_agent = "AmigaVoyager/3.2 (AmigaOS/MC680x0)"
        self.proxy_port = proxy_port

        # List to avoid requesting the same URL twice
        self.crawled_urls = set ()

        # Seconds to wait a connection before giving up
        self.timeout = 360

        logging.info ("Crawler initialized to start from: " + self.initial_url)


    def start (self):
        """
        Starts the crawler
        """
        self.scrape_page (self.initial_url)


    def process_page (self, url, parsed):
        """
        Extracts the information from the webpage, and logs it

        Args:
            url -> URL of the webpage

            parsed -> Object returned by BeautifulSoup with the parsed HTML
        """

        # Extracts title and URL of the webpage
        title = parsed.title
        title = title.text if title else "-"

        description = parsed.find ("meta", attrs = {"name": "description"})
        description = description ["content"] if description else "-"

        # Substitutes " with '
        msg = ("\"" + re.sub ("\"", "'", url)
                + "\",\"" + re.sub ("\"", "'", title.strip ("\r\n\t"))
                + "\",\"" + re.sub ("\"", "'", description.strip (" \r\n\t"))
                + "\""
        )

        print (" => " + msg)
        sys.stdout.flush ()


    def urlopen (self, url):
        """
        Uses pycurl to fetch a site using the local proxy on the SOCKS_PORT.
        """
        output = io.BytesIO ()

        query = pycurl.Curl ()
        query.setopt (pycurl.URL, url)
        query.setopt (pycurl.USERAGENT, self.user_agent)

        if self.proxy_port:
            query.setopt (pycurl.PROXY, '127.0.0.1')
            query.setopt (pycurl.PROXYPORT, self.proxy_port)
            query.setopt (pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)

        # Follow redirects
        query.setopt (pycurl.FOLLOWLOCATION, 1)
        query.setopt (pycurl.CONNECTTIMEOUT, self.timeout)
        query.setopt (pycurl.WRITEFUNCTION, output.write)

        query.perform ()
        return output.getvalue ()


    def scrape_page (self, url, current_depth = 0):
        """
        Scrapes the given webpage, looking for links to other pages recursively.
        The strategy used is depth-first search.


        Args:
            url -> URL of the webpage to get links from

            current_depth (OPTIONAL) -> Current depth of the recursion
        """
        logging.info ("Processing " + url)
        logging.info ("Current depth: " + str (current_depth))

        # Checks the maximum depth
        if current_depth > self.max_depth:
            logging.debug ("Max depth reached when processing " + url)
            return

        try:
            html = self.urlopen (url)
        except Exception as e:
            logging.error ("Skipping processing of " + url + " -> " + str (e))
            return

        parsed = BeautifulSoup (html, "html5lib")

        # Processes the webpage info
        self.process_page (url, parsed)

        # Gets all anchors
        tag = parsed.find ("a", href = True)
        while tag is not None:

            # Gets the destination and also scrapes that page
            href = tag ["href"]

            # Updates the value of 'tag' to be the next anchor
            tag = tag.find_next ("a", href = True)

            logging.debug ("Extracted href: " + href)

            parsed_url = urlparse (href)

            # If it was a relative link, constructs
            if not parsed_url.netloc and not parsed_url.scheme:
                # An empty 'netloc' attribute means that it was a relative path
                base_url = urlparse (url)

                # Gets only the path and query of the resource, without fragment
                # (the final #<id>)
                rel_path = parsed_url.path.strip ("/")

                if parsed_url.query:
                    rel_path += "?" + parsed_url.query

                new_url = base_url.scheme + "://" + base_url.netloc + "/" + rel_path

            elif parsed_url.scheme == "http" or parsed_url.scheme == "https":

                new_url = href

            else:
                # Skips the link
                logging.info ("Skipping processing of " + href)
                continue


            # Also, discards the already crawled pages
            if new_url == url or new_url in self.crawled_urls:
                continue

            self.crawled_urls.add (new_url)

            # Scrapes the new page, increasing the recursiong depth
            self.scrape_page (new_url, current_depth + 1)
