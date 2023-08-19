#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import gzip
import time
from multiprocessing import cpu_count, Queue, Process, current_process
import logging

import re
import os.path
from db.model import Block
from db.helper import setup_connection
from netaddr import iprange_to_cidrs
import math

VERSION = '2.0'
FILELIST = ['afrinic.db.gz', 'apnic.db.inet6num.gz', 'apnic.db.inetnum.gz', 'arin.db.gz',
            'lacnic.db.gz', 'ripe.db.inetnum.gz', 'ripe.db.inet6num.gz']
NUM_WORKERS = cpu_count()
LOG_FORMAT = '%(asctime)-15s - %(name)-9s - %(levelname)-8s - %(processName)-11s - %(filename)s - %(message)s'
COMMIT_COUNT = 10000
NUM_BLOCKS = 0
CURRENT_FILENAME = "empty"


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.filename = CURRENT_FILENAME
        return True


logger = logging.getLogger('create_db')
logger.setLevel(logging.INFO)
f = ContextFilter()
logger.addFilter(f)
formatter = logging.Formatter(LOG_FORMAT)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def get_source(filename: str):
    if filename.startswith('afrinic'):
        return b'afrinic'
    elif filename.startswith('apnic'):
        return b'apnic'
    elif filename.startswith('arin'):
        return b'arin'
    elif 'lacnic' in filename:
        return b'lacnic'
    elif filename.startswith('ripe'):
        return b'ripe'
    else:
        logger.error(f"Can not determine source for {filename}")
    return None


def parse_property(block: str, name: str) -> str:
    match = re.findall(b'^%s:\s?(.+)$' % (name), block, re.MULTILINE)
    if match:
        # remove empty lines and remove multiple names
        x = b' '.join(list(filter(None, (x.strip().replace(
            b"%s: " % name, b'').replace(b"%s: " % name, b'') for x in match))))
        # remove multiple whitespaces by using a split hack
        # decode to latin-1 so it can be inserted in the database
        return ' '.join(x.decode('latin-1').split())
    else:
        return None


def parse_property_inetnum(block: str) -> str:
    # IPv4
    match = re.findall(
        rb'^inetnum:[\s]*((?:\d{1,3}\.){3}\d{1,3})[\s]*-[\s]*((?:\d{1,3}\.){3}\d{1,3})', block, re.MULTILINE)
    if match:
        # netaddr can only handle strings, not bytes
        ip_start = match[0][0].decode('utf-8')
        ip_end = match[0][1].decode('utf-8')
        cidrs = iprange_to_cidrs(ip_start, ip_end)
        return cidrs
    # IPv6
    match = re.findall(
        rb'^inet6num:[\s]*([0-9a-fA-F:\/]{1,43})', block, re.MULTILINE)
    if match:
        return match[0]
    # LACNIC translation for IPv4
    match = re.findall(
        rb'^inet4num:[\s]*((?:\d{1,3}\.){3}\d{1,3}/\d{1,2})', block, re.MULTILINE)
    if match:
        return match[0]
    # ARIN route IPv4
    match = re.findall(
        rb'^route:[\s]*((?:\d{1,3}\.){3}\d{1,3}/\d{1,2})', block, re.MULTILINE)
    if match:
        return match[0]
    # ARIN route6 IPv6
    match = re.findall(
        rb'^route6:[\s]*([0-9a-fA-F:\/]{1,43})', block, re.MULTILINE)
    if match:
        return match[0]
    logger.warning(f"Could not parse inetnum on block {block}")
    return None


def read_blocks(filename: str) -> list:
    if filename.endswith('.gz'):
        opemethod = gzip.open
    else:
        opemethod = open
    cust_source = get_source(filename.split('/')[-1])
    single_block = b''
    blocks = []

    with opemethod(filename, mode='rb') as f:
        for line in f:
            # skip comments
            if line.startswith(b'%') or line.startswith(b'#') or line.startswith(b'remarks:'):
                continue
            # block end
            if line.strip() == b'':
                if single_block.startswith(b'inetnum:') or single_block.startswith(b'inet6num:') or single_block.startswith(b'route:') or single_block.startswith(b'route6:'):
                    # add source
                    single_block += b"cust_source: %s" % (cust_source)
                    blocks.append(single_block)
                    if len(blocks) % 1000 == 0:
                        logger.debug(
                            f"parsed another 1000 blocks ({len(blocks)} so far)")
                    single_block = b''
                    # comment out to only parse x blocks
                    # if len(blocks) == 100:
                    #    break
                else:
                    single_block = b''
            else:
                single_block += line
    logger.info(f"Got {len(blocks)} blocks")
    global NUM_BLOCKS
    NUM_BLOCKS = len(blocks)
    return blocks


def parse_blocks(jobs: Queue, connection_string: str):
    session = setup_connection(connection_string)

    counter = 0
    BLOCKS_DONE = 0

    start_time = time.time()
    while True:
        block = jobs.get()
        if block is None:
            break

        inetnum = parse_property_inetnum(block)
        netname = parse_property(block, b'netname')
        # No netname field in ARIN block, try origin
        if not netname:
            netname = parse_property(block, b'origin')
        description = parse_property(block, b'descr')
        country = parse_property(block, b'country')
        # if we have a city object, append it to the country
        city = parse_property(block, b'city')
        if city:
            country = f"{country} - {city}"
        maintained_by = parse_property(block, b'mnt-by')
        created = parse_property(block, b'created')
        last_modified = parse_property(block, b'last-modified')
        if not last_modified:
            last_modified = parse_property(block, b'changed')
        status = parse_property(block, b'status')
        source = parse_property(block, b'cust_source')

        if isinstance(inetnum, list):
            for cidr in inetnum:
                b = Block(inetnum=str(cidr), netname=netname, description=description, country=country,
                          maintained_by=maintained_by, created=created, last_modified=last_modified, source=source, status=status)
                session.add(b)
        else:
            b = Block(inetnum=inetnum.decode('utf-8'), netname=netname, description=description, country=country,
                      maintained_by=maintained_by, created=created, last_modified=last_modified, source=source, status=status)
            session.add(b)

        counter += 1
        BLOCKS_DONE += 1
        if counter % COMMIT_COUNT == 0:
            session.commit()
            session.close()
            session = setup_connection(connection_string)
            # not really accurate at the moment
            percent = (BLOCKS_DONE * NUM_WORKERS * 100) / NUM_BLOCKS
            if percent > 100:
                percent = 100
            logger.debug('committed {} blocks ({} seconds) {:.1f}% done.'.format(
                counter, round(time.time() - start_time, 2), percent))
            counter = 0
            start_time = time.time()
    session.commit()
    logger.debug('committed last blocks')
    session.close()
    logger.debug(f"{current_process().name} finished")


def main(connection_string):
    overall_start_time = time.time()
    session = setup_connection(connection_string, create_db=True)

    for entry in FILELIST:
        global CURRENT_FILENAME
        CURRENT_FILENAME = entry
        f_name = f"./databases/{entry}"
        if os.path.exists(f_name):
            logger.info(f"parsing database file: {f_name}")
            start_time = time.time()
            blocks = read_blocks(f_name)
            logger.info(
                f"database parsing finished: {round(time.time() - start_time, 2)} seconds")

            logger.info('parsing blocks')
            start_time = time.time()

            jobs = Queue()

            workers = []
            # start workers
            logger.debug(f"starting {NUM_WORKERS} processes")
            for w in range(NUM_WORKERS):
                p = Process(target=parse_blocks, args=(
                    jobs, connection_string,), daemon=True)
                p.start()
                workers.append(p)

            # add tasks
            for b in blocks:
                jobs.put(b)
            for i in range(NUM_WORKERS):
                jobs.put(None)
            jobs.close()
            jobs.join_thread()

            # wait to finish
            for p in workers:
                p.join()

            logger.info(
                f"block parsing finished: {round(time.time() - start_time, 2)} seconds")
        else:
            logger.info(
                f"File {f_name} not found. Please download using download_dumps.sh")

    CURRENT_FILENAME = "empty"
    logger.info(
        f"script finished: {round(time.time() - overall_start_time, 2)} seconds")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create DB')
    parser.add_argument('-c', dest='connection_string', type=str,
                        required=True, help="Connection string to the postgres database")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="set loglevel to DEBUG")
    parser.add_argument('--version', action='version',
                        version=f"%(prog)s {VERSION}")
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    main(args.connection_string)
