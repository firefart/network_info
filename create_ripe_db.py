#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gzip
import time
from multiprocessing import cpu_count, Queue, Process, current_process
import logging

import re
import os.path
from db.model import Block
from db.helper import setup_connection
from netaddr import iprange_to_cidrs

FILELIST = ['ripe.db.inetnum.gz', 'ripe.db.inet6num.gz']
NUM_WORKERS = cpu_count()
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(processName)s - %(message)s'
COMMIT_COUNT = 10000
NUM_BLOCKS = 0

logger = logging.getLogger('create_ripe_db')
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
#        logger.info('Missing ' + name + ' in block')
        return None

def parse_property_inetnum(block: str):
    match = re.findall(u'^{0:s}:\s*(.*)$'.format('inetnum'), block, re.MULTILINE)
    if match:
        ip_start = match[0].split(' - ')[0]
        ip_end = match[0].split(' - ')[1]
        cidrs = iprange_to_cidrs(ip_start, ip_end)
        return '{}'.format(cidrs[0])
    else:
        match = re.findall(u'^{0:s}:\s*(.*)$'.format('inet6num'), block, re.MULTILINE)
        if match:
            return " ".join(match)
        else:
            return None


def read_blocks(filename: str) -> list:
    f = gzip.open(filename, mode='rt', encoding='ISO-8859-1')
    single_block = ''
    blocks = []
    for line in f:
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
            single_block += line
    f.close()
    logger.info('Got {} blocks'.format(len(blocks)))
    global NUM_BLOCKS
    NUM_BLOCKS = len(blocks)
    return blocks


def parse_blocks(jobs: Queue):
    session = setup_connection()

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
            session = setup_connection()
            logger.debug('committed {} blocks ({} seconds) {:.1f}% done.'.format(counter, round(time.time() - start_time, 2),BLOCKS_DONE * NUM_WORKERS * 100 / NUM_BLOCKS))
            counter = 0
            start_time = time.time()
    session.commit()
    logger.debug('committed last blocks')
    session.close()
    logger.debug('{} finished'.format(current_process().name))



def main():
    overall_start_time = time.time()

    session = setup_connection(create_db=True)

    for FILENAME in FILELIST:
        if os.path.exists(FILENAME):
            logger.info('parsing ripe database file: {}'.format(FILENAME))
            start_time = time.time()
            blocks = read_blocks(FILENAME)
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
        else:
            logger.info('File {} not found. Please download from ftp://ftp.ripe.net/ripe/dbase/split/{}'.format(FILENAME, FILENAME))

    logger.info('script finished: {} seconds'.format(round(time.time() - overall_start_time, 2)))


if __name__ == '__main__':
    main()
