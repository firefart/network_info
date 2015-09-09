#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gzip
import time
from multiprocessing import cpu_count, Queue, Process, current_process
import logging

import re
import os.path
from db.model import Block, Cidr
from db.helper import setup_connection
from netaddr import iprange_to_cidrs

RIPE_FILENAME = 'ripe.db.inetnum.gz'
NUM_WORKERS = cpu_count()
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(processName)s - %(message)s'
COMMIT_COUNT = 10000

logger = logging.getLogger('create_ripe_db')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(LOG_FORMAT)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)


def parse_property(block: str, name: str):
    match = re.search(u'^{0:s}:\s*(.*)$'.format(name), block, re.MULTILINE)
    if match:
        return match.group(1)
    else:
        logger.error('Missing ' + name + ' in block')
        return None


def read_blocks() -> list:
    if not os.path.exists(RIPE_FILENAME):
        raise Exception('Please download the Ripe database from ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inetnum.gz')
    f = gzip.open(RIPE_FILENAME, mode='rt', encoding='ISO-8859-1')
    single_block = ''
    blocks = []
    for line in f:
        if line.startswith('%') or line.startswith('#') or line.startswith('remarks:'):
            continue
        # block end
        if line.strip() == '':
            if single_block.startswith('inetnum:'):
                blocks.append(single_block)
                single_block = ''
                # comment out to only parse x blocks
                # if len(blocks) == 100:
                #    break
        else:
            single_block += line
    f.close()
    logger.info('Got {} blocks'.format(len(blocks)))
    return blocks


def parse_blocks(jobs: Queue):
    session = setup_connection()

    counter = 0
    start_time = time.time()
    while True:
        block = jobs.get()
        if block is None:
            break

        inetnum = parse_property(block, 'inetnum')
        netname = parse_property(block, 'netname')
        description = parse_property(block, 'descr')
        country = parse_property(block, 'country')
        maintained_by = parse_property(block, 'mnt-by')
        b = Block(inetnum=inetnum, netname=netname, description=description, country=country,
                  maintained_by=maintained_by)
        session.add(b)
        counter += 1
        if counter % COMMIT_COUNT == 0:
            session.commit()
            session.close()
            session = setup_connection()
            logger.debug('committed {} blocks ({} seconds)'.format(counter, round(time.time() - start_time, 2)))
            counter = 0
            start_time = time.time()
    session.commit()
    logger.debug('committed last blocks')
    session.close()
    logger.debug('{} finished'.format(current_process().name))


def parse_ips(jobs: Queue):
    session = setup_connection()

    counter = 0
    start_time = time.time()
    while True:
        block = jobs.get()
        if block is None:
            break

        ip_start = block.inetnum.split(' - ')[0]
        ip_end = block.inetnum.split(' - ')[1]

        cidrs = iprange_to_cidrs(ip_start, ip_end)
        for c in cidrs:
            session.add(Cidr(cidr=str(c), block=block))
        counter += 1
        if counter % COMMIT_COUNT == 0:
            session.commit()
            session.close()
            session = setup_connection()
            logger.debug('committed cidrs ({} seconds)'.format(round(time.time() - start_time, 2)))
            counter = 0
            start_time = time.time()

    session.commit()
    logger.debug('committed last cidrs')
    session.close()
    logger.debug('{} finished'.format(current_process().name))


def main():
    overall_start_time = time.time()

    session = setup_connection(create_db=True)

    logger.info('parsing ripe database')
    start_time = time.time()
    blocks = read_blocks()
    logger.info('ripe database parsing finished: {} seconds'.format(round(time.time() - start_time, 2)))

    logger.info('parsing blocks')
    start_time = time.time()

    jobs = Queue()

    workers = []
    # start workers
    logger.debug('starting {} processes'.format(NUM_WORKERS))
    for w in range(NUM_WORKERS):
        p = Process(target=parse_blocks, args=(jobs,))
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

    logger.info('parsing IPs')

    start_time = time.time()
    jobs = Queue()

    workers = []
    # start workers
    logger.debug('starting {} processes'.format(NUM_WORKERS))
    for w in range(NUM_WORKERS):
        p = Process(target=parse_ips, args=(jobs,))
        p.start()
        workers.append(p)

    # add tasks
    logger.debug('populating job queue')
    for b in session.query(Block):
        jobs.put(b)
    session.close()
    for i in range(NUM_WORKERS):
        jobs.put(None)
    logger.debug('job queue populated')

    # wait to finish
    for p in workers:
        p.join()

    logger.info('ip parsing finished: {} seconds'.format(round(time.time() - start_time, 2)))

    logger.info('script finished: {} seconds'.format(round(time.time() - overall_start_time, 2)))


if __name__ == '__main__':
    main()
