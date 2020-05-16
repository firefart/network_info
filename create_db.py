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
FILELIST = ['afrinic.db.gz', 'apnic.db.inet6num.gz', 'apnic.db.inetnum.gz', 'arin.db',
            'delegated-lacnic-extended-latest', 'ripe.db.inetnum.gz', 'ripe.db.inet6num.gz']
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
        return 'afrinic'
    elif filename.startswith('apnic'):
        return 'apnic'
    elif filename.startswith('arin'):
        return 'arin'
    elif 'lacnic' in filename:
        return 'lacnic'
    elif filename.startswith('ripe'):
        return 'ripe'
    else:
        logger.error(f"Can not determine source for {filename}")
    return None


def parse_property(block: str, name: str):
    match = re.findall(u'^{0:s}:\s?(.+)$'.format(name), block, re.MULTILINE)
    if match:
        # remove whitespaces and empty lines
        return ' '.join(list(filter(None, (x.strip() for x in match))))
    else:
        return None


def parse_property_inetnum(block: str):
    # IPv4
    match = re.findall(
        r'^inetnum:[\s]*((?:\d{1,3}\.){3}\d{1,3})[\s]*-[\s]*((?:\d{1,3}\.){3}\d{1,3})', block, re.MULTILINE)
    if match:
        ip_start = match[0][0]
        ip_end = match[0][1]
        cidrs = iprange_to_cidrs(ip_start, ip_end)
        return cidrs
    # IPv6
    match = re.findall(
        r'^inet6num:[\s]*([0-9a-fA-F:\/]{1,43})', block, re.MULTILINE)
    if match:
        return match[0]
    # LACNIC translation for IPv4
    match = re.findall(
        r'^inet4num:[\s]*((?:\d{1,3}\.){3}\d{1,3}/\d{1,2})', block, re.MULTILINE)
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
    single_block = ''
    blocks = []

    with opemethod(filename, mode='rt', encoding='ISO-8859-1') as f:
        # Translation for LACNIC DB
        if filename.endswith('delegated-lacnic-extended-latest'):
            for line in f:
                line = line.strip()
                if line.startswith('lacnic'):
                    elements = line.split('|')
                    if len(elements) >= 7:
                        # convert lacnic to ripe format
                        single_block = ''
                        if elements[2] == 'ipv4':
                            single_block += 'inet4num: ' + \
                                elements[3] + '/' + \
                                str(int(math.log(4294967296 /
                                                 int(elements[4]), 2))) + '\n'
                        elif elements[2] == 'ipv6':
                            single_block += 'inet6num: ' + \
                                elements[3] + '/' + elements[4] + '\n'
                        elif elements[2] == 'asn':
                            continue
                        else:
                            logger.warning(
                                f"Unknown inetnum type {elements[2]} on line {line}")
                            continue
                        if len(elements[1]) > 1:
                            single_block += 'country: ' + elements[1] + '\n'
                        if elements[5].isnumeric():
                            single_block += 'last-modified: ' + \
                                elements[5] + '\n'
                        single_block += 'descr: ' + elements[6] + '\n'
                        if not any(x in single_block for x in ['inet4num', 'inet6num']):
                            logger.warning(
                                f"Invalid block: {line} {single_block}")
                        single_block += f"cust_source: {cust_source}"
                        blocks.append(single_block)
                    else:
                        logger.warning(f"Invalid line: {line}")
                else:
                    logger.warning(f"line does not start with lacnic: {line}")
        # All other DBs goes here
        else:
            for line in f:
                # skip comments
                if line.startswith('%') or line.startswith('#') or line.startswith('remarks:'):
                    continue
                # block end
                if line.strip() == '':
                    if single_block.startswith('inetnum:') or single_block.startswith('inet6num:'):
                        # add source
                        single_block += f"cust_source: {cust_source}"
                        blocks.append(single_block)
                        if len(blocks) % 1000 == 0:
                            logger.debug(
                                f"parsed another 1000 blocks ({len(blocks)} so far)")
                        single_block = ''
                        # comment out to only parse x blocks
                        # if len(blocks) == 100:
                        #    break
                    else:
                        single_block = ''
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
        netname = parse_property(block, 'netname')
        description = parse_property(block, 'descr')
        country = parse_property(block, 'country')
        maintained_by = parse_property(block, 'mnt-by')
        created = parse_property(block, 'created')
        last_modified = parse_property(block, 'last-modified')
        source = parse_property(block, 'cust_source')

        if isinstance(inetnum, list):
            for cidr in inetnum:
                b = Block(inetnum=str(cidr), netname=netname, description=description, country=country,
                          maintained_by=maintained_by, created=created, last_modified=last_modified, source=source)
                session.add(b)
        else:
            b = Block(inetnum=inetnum, netname=netname, description=description, country=country,
                      maintained_by=maintained_by, created=created, last_modified=last_modified, source=source)
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
                    jobs, connection_string,))
                p.start()
                workers.append(p)

            # add tasks
            for b in blocks:
                jobs.put(b)
            for i in range(NUM_WORKERS):
                jobs.put(None)

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
