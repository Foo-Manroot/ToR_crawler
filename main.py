#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Little program to crawl some ToR pages and demonstrate the usage of the Stem API to
connect ToR from within Python.

This is the main script. The crawler is implemented in ./crawler.py

Made by Foo-Manroot
Last change on Feb 04, 2018

API used for ToR: https://stem.torproject.org/
To check the IP, https://www.ipify.org/ was used
"""

import logging \
        , sys      \
        , argparse \
        , urllib.request

# To set up the proxy
import socks \
    , socket

# API to access ToR
import stem.process

# To start the spider
import crawler

####
# GLOBAL PARAMETERS
####
SOCKS_PORT = 1234
CHECK_IP_ENDPOINT = "https://api.ipify.org/?format=text"
DEFAULT_URL = "https://foo-manroot.github.io/"


def show_msg (m):
    """
    Prints the message on STDOUT with a little formatting

    Args:
        m -> A string with the message to print out
    """
    print (" => " + m)
    sys.stdout.flush ()


def port_type (value):
    """
    Checks that the given value is an integer between 0 an 65535

    Args:
        -> value: The value to check
    Returns:
        The value, as an integer
    Raises:
        -> argparse.ArgumentTypeError, if the argument wasn't a positive integer
    """
    ivalue = int (value)
    if ivalue < 0 or ivalue > 65535:
        raise argparse.ArgumentTypeError (value + " is an invalid port value")
    return ivalue

def depth_type (value):
    """
    Checks that the given value is a positive integer

    Args:
        -> value: The value to check
    Returns:
        The value, as an integer
    Raises:
        -> argparse.ArgumentTypeError, if the argument wasn't a positive integer
    """
    ivalue = int (value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError (value + " is an invalid positive int value")
    return ivalue


def parse_args ():
    """
    Parses the CLI arguments

    Returns:
        An object with the parsed arguments
    """
    parser = argparse.ArgumentParser ()

    parser.add_argument ("-v", "--verbose"
                        , help = "Increases the verbosity level (up to 3). "
                                + "By default, it's 2"
                        , action = "count"
                        , default = 2
    )

    parser.add_argument ("-u", "--url"
                        , help = "Initial URL to start crawling. "
                            + "By default, it's '" + DEFAULT_URL + "'"
                        , type = str
                        , default = DEFAULT_URL
    )

    parser.add_argument ("-p", "--port"
                        , help = "Port where the local proxy will be listening. "
                            + "By default, it's " + str (SOCKS_PORT)
                        , type = port_type
                        , default = SOCKS_PORT
    )

    parser.add_argument ("-d", "--depth"
                        , help = "Maximum depth for the recursive calls to"
                            + " scrape pages. By default, it's 2"
                        , type = depth_type
                        , default = 2
    )


    args = parser.parse_args ()

    return args


def config_logger (parsed_args):
    """
    Configures the logger to be used the rest of the execution of this script

    Args:
            parsed_args -> Object with the parsed arguments, used to set
                the configuration
    """
    verbosity = parsed_args.verbose

    # Mapping of the different verbosity values with the logging levels
    verb_map = {
        0: logging.CRITICAL
        , 1: logging.ERROR
        , 2: logging.WARNING
        , 3: logging.INFO
        , 4: logging.DEBUG
        , 5: logging.NOTSET
    }

    logging.basicConfig (
        level = verb_map [min (verbosity, len (verb_map) - 1)]
        , format= '[%(asctime)s] %(levelname)s - %(message)s'
        , datefmt='%H:%M:%S'
    )


def print_bootstrap_lines (line):
    """
    Handler to show the bootstrapping progress of ToR
    """
    if "Bootstrapped " in line:
        logging.info (line)


def setup_proxy (port = SOCKS_PORT):
    """
    Sets up urllib2 to use the SOCKS proxy on 127.0.0.1:<port>

    Args:
            port -> Port where the local proxy is listening on
    """
    logging.debug ("Setting up proxy on socks5://127.0.0.1:" + str (port))

    socks.setdefaultproxy (socks.PROXY_TYPE_SOCKS5, '127.0.0.1', port)
    socket.socket = socks.socksocket

    logging.debug ("Proxy installed")


def get_ip ():
    """
    Performs a request to https://www.ipify.org/ and returns the external IP of
    this machine

    Returns:
            A string with the returned representation of the IP

    Throws:
            Every exception that may have been thrown by
    """
    logging.debug ("Performing a request to " + CHECK_IP_ENDPOINT)
    ip = urllib.request.urlopen (CHECK_IP_ENDPOINT).read ()

    return ip.decode ("utf-8")

####
# MAIN
####
if __name__ == "__main__":

    args = parse_args ()
    config_logger (args)

    initial_url = args.url
    proxy_port = args.port
    max_depth = args.depth

    try:
        original_ip = get_ip ()

        show_msg ("The original IP address is: " + original_ip)

        # Changes the address using ToR
        show_msg ("Starting ToR")
        tor_process = stem.process.launch_tor_with_config (
                config = {
                'SocksPort': str (proxy_port)
            }
            , init_msg_handler = print_bootstrap_lines
        )
        show_msg ("ToR started")

        setup_proxy (proxy_port)

        ip = get_ip ()
        show_msg ("New IP: " + ip)

        # Checks that the IP has indeed changed
        if ip == original_ip:
            logging.fatal ("The IP hasn't changed")
            raise ValueError ("Error setting up the proxy")

        # Starts the crawler
        spider = crawler.Crawler (
                    initial_url
                    , proxy_port = proxy_port
                    , max_depth = max_depth
        )
        spider.start ()

    except Exception as e:
        logging.fatal ("Exception caught: " + str (e) + "\nShutting down...")

    except KeyboardInterrupt:
        logging.info ("Interrupt caught.\nShutting down...")

    finally:
        # Stops ToR
        try:
            tor_process.kill ()
            logging.info ("ToR process shut down")
        except NameError:
            # The process hasn't been started yet
            pass
