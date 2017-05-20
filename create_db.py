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
FILELIST = ['afrinic.db.gz', 'apnic.db.inet6num.gz', 'apnic.db.inetnum.gz', 'arin.db', 'delegated-lacnic-extended-latest', 'ripe.db.inetnum.gz', 'ripe.db.inet6num.gz']
NUM_WORKERS = cpu_count()
LOG_FORMAT = '%(asctime)-15s - %(name)-9s - %(levelname)-8s - %(processName)-11s - %(message)s'
COMMIT_COUNT = 10000
NUM_BLOCKS = 0

logger = logging.getLogger('create_db')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(LOG_FORMAT)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)


def parse_property(block: str, name: str):
    match = re.findall(u'^{0:s}:\s*(.*)$'.format(name), block, re.MULTILINE)
    if match:
        return " ".join(match)
    else:
        return None

def parse_property_inetnum(block: str):
    # IPv4
    match = re.findall(r'^inetnum:[\s]*((?:\d{1,3}\.){3}\d{1,3})[\s]*-[\s]*((?:\d{1,3}\.){3}\d{1,3})', block, re.MULTILINE)
    if match:
        ip_start = match[0][0]
        ip_end = match[0][1]
        cidrs = iprange_to_cidrs(ip_start, ip_end)
        return '{}'.format(cidrs[0])
    # IPv6
    match = re.findall('^inet6num:[\s]*([0-9a-fA-F:\/]{1,43})', block, re.MULTILINE)
    if match:
        return match[0]
    # LACNIC translation for IPv4
    match = re.findall('^inet4num:[\s]*((?:\d{1,3}\.){3}\d{1,3}/\d{1,2})', block, re.MULTILINE)
    if match:
        return match[0]
    logger.warn("Could not parse inetnum on block {}".format(block))
    return None


def read_blocks(filename: str) -> list:
    if filename.endswith('.gz'):
        f = gzip.open(filename, mode='rt', encoding='ISO-8859-1')
    else:
        f = open(filename, mode='rt', encoding='ISO-8859-1')
    single_block = ''
    blocks = []

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
                        single_block += 'inet4num: ' + elements[3] + '/' + str(int(math.log(4294967296/int(elements[4]),2))) + '\n'
                    elif elements[2] == 'ipv6':
                        single_block += 'inet6num: ' + elements[3] + '/' + elements[4] + '\n'
                    elif elements[2] == 'asn':
                        continue
                    else:
                        logger.warn("Unknown inetnum type {} on line {}".format(elements[2], line))
                        continue
                    if len(elements[1]) > 1:
                        single_block += 'country: ' + elements[1] + '\n'
                    if elements[5].isnumeric():
                        single_block += 'last-modified: ' + elements[5] + '\n'
                    single_block += 'descr: ' + elements[6] + '\n'
                    if not any(x in single_block for x in ['inet4num', 'inet6num']):
                        logger.warn("Invalid block: {} {}".format(line, single_block))
                    blocks.append(single_block)
                else:
                    logger.warn("Invalid line: {}".format(line))
            else:
                logger.warn("line does not start with lacnic: {}".format(line))
    # All other DBs goes here
    else:
        for line in f:
            # skip comments
            if line.startswith('%') or line.startswith('#') or line.startswith('remarks:'):
                continue
            # block end
            if line.strip() == '':
                if single_block.startswith('inetnum:') or single_block.startswith('inet6num:'):
                    blocks.append(single_block)
                    single_block = ''
                    # comment out to only parse x blocks
                    # if len(blocks) == 100:
                    #    break
                else:
                    single_block = ''
            else:
                single_block += line

    f.close()
    logger.info('Got {} blocks'.format(len(blocks)))
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

        b = Block(inetnum=inetnum, netname=netname, description=description, country=country,
                  maintained_by=maintained_by, created=created, last_modified=last_modified)

        session.add(b)
        counter += 1
        BLOCKS_DONE += 1
        if counter % COMMIT_COUNT == 0:
            session.commit()
            session.close()
            session = setup_connection(connection_string)
            logger.debug('committed {} blocks ({} seconds) {:.1f}% done.'.format(counter, round(time.time() - start_time, 2), BLOCKS_DONE * NUM_WORKERS * 100 / NUM_BLOCKS))
            counter = 0
            start_time = time.time()
    session.commit()
    logger.debug('committed last blocks')
    session.close()
    logger.debug('{} finished'.format(current_process().name))


def main(connection_string):
    overall_start_time = time.time()
    session = setup_connection(connection_string, create_db=True)

    for entry in FILELIST:
        f_name = "./databases/{}".format(entry)
        if os.path.exists(f_name):
            logger.info('parsing database file: {}'.format(f_name))
            start_time = time.time()
            blocks = read_blocks(f_name)
            logger.info('database parsing finished: {} seconds'.format(round(time.time() - start_time, 2)))

            logger.info('parsing blocks')
            start_time = time.time()

            jobs = Queue()

            workers = []
            # start workers
            logger.debug('starting {} processes'.format(NUM_WORKERS))
            for w in range(NUM_WORKERS):
                p = Process(target=parse_blocks, args=(jobs,connection_string,))
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

            logger.info('block parsing finished: {} seconds'.format(round(time.time() - start_time, 2)))
        else:
            logger.info('File {} not found. Please download using download_dumps.sh'.format(f_name))

    logger.info('script finished: {} seconds'.format(round(time.time() - overall_start_time, 2)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create DB')
    parser.add_argument('-c', dest='connection_string', type=str, required=True, help="Connection string to the postgres database")
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(VERSION))
    args = parser.parse_args()
    main(args.connection_string)
