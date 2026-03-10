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

VERSION = '2.0'
FILELIST = ['afrinic.db.gz','apnic.db.inet6num.gz','apnic.db.inetnum.gz','arin.db.gz','lacnic.db.gz','ripe.db.inetnum.gz','ripe.db.inet6num.gz']
NUM_WORKERS = cpu_count()
LOG_FORMAT = '%(asctime)-15s - %(name)-9s - %(levelname)-8s - %(processName)-11s - %(message)s'
COMMIT_COUNT = 10000

logger = logging.getLogger('create_db')
logger.setLevel(logging.INFO)
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
        logger.error(f"Cannot determine source for {filename}")
    return None

def parse_property(block: bytes, name: bytes):
    match = re.findall(b'^%s:\s?(.+)$' % name, block, re.MULTILINE)
    if match:
        x = b' '.join(list(filter(None,(x.strip().replace(b"%s: " % name, b'').replace(b"%s: " % name, b'') for x in match))))
        return ' '.join(x.decode('latin-1').split())
    return None

def parse_property_inetnum(block: bytes):
    match = re.findall(rb'^inetnum:[\s]*((?:\d{1,3}\.){3}\d{1,3})[\s]*-[\s]*((?:\d{1,3}\.){3}\d{1,3})', block, re.MULTILINE)
    if match:
        ip_start = match[0][0].decode('utf-8')
        ip_end = match[0][1].decode('utf-8')
        return iprange_to_cidrs(ip_start, ip_end)
    match = re.findall(rb'^inetnum:[\s]*((?:\d{1,3}\.){3}\d{1,3}/\d+)', block, re.MULTILINE)
    if match:
        return match[0]
    match = re.findall(rb'^inetnum:[\s]*((?:\d{1,3}\.){2}\d{1,3}/\d+)', block, re.MULTILINE)
    if match:
        tmp = match[0].split(b"/")
        return f"{tmp[0].decode('utf-8')}.0/{tmp[1].decode('utf-8')}".encode("utf-8")
    match = re.findall(rb'^inetnum:[\s]*((?:\d{1,3}\.){1}\d{1,3}/\d+)', block, re.MULTILINE)
    if match:
        tmp = match[0].split(b"/")
        return f"{tmp[0].decode('utf-8')}.0.0/{tmp[1].decode('utf-8')}".encode("utf-8")
    match = re.findall(rb'^inet6num:[\s]*([0-9a-fA-F:\/]{1,43})', block, re.MULTILINE)
    if match:
        return match[0]
    match = re.findall(rb'^route:[\s]*((?:\d{1,3}\.){3}\d{1,3}/\d{1,2})', block, re.MULTILINE)
    if match:
        return match[0]
    match = re.findall(rb'^route6:[\s]*([0-9a-fA-F:\/]{1,43})', block, re.MULTILINE)
    if match:
        return match[0]
    return None

def read_blocks(filename: str):
    openmethod = gzip.open if filename.endswith('.gz') else open
    cust_source = get_source(filename.split('/')[-1])
    single_block = b''
    blocks = []
    with openmethod(filename, mode='rb') as f:
        for line in f:
            if line.startswith((b'%', b'#', b'remarks:')):
                continue
            if line.strip() == b'':
                if single_block.startswith((b'inetnum:', b'inet6num:', b'route:', b'route6:')):
                    single_block += b"cust_source: %s" % cust_source
                    blocks.append(single_block)
                    single_block = b''
                else:
                    single_block = b''
            else:
                single_block += line
    logger.info(f"Got {len(blocks)} blocks")
    return blocks

def parse_blocks(jobs: Queue, connection_string: str, total_blocks: int):
    session = setup_connection(connection_string)
    counter = 0
    blocks_done = 0
    start_time = time.time()
    while True:
        block = jobs.get()
        if block is None:
            break
        inetnum = parse_property_inetnum(block)
        if not inetnum:
            continue
        netname = parse_property(block, b'netname') or parse_property(block, b'origin')
        description = parse_property(block, b'descr')
        country = parse_property(block, b'country')
        city = parse_property(block, b'city')
        if city:
            country = f"{country} - {city}"
        maintained_by = parse_property(block, b'mnt-by')
        created = parse_property(block, b'created')
        last_modified = parse_property(block, b'last-modified')
        status = parse_property(block, b'status')
        source = parse_property(block, b'cust_source')
        if isinstance(inetnum, list):
            for cidr in inetnum:
                session.add(Block(inetnum=str(cidr), netname=netname, description=description, country=country, maintained_by=maintained_by, created=created, last_modified=last_modified, source=source, status=status))
        else:
            session.add(Block(inetnum=inetnum.decode('utf-8'), netname=netname, description=description, country=country, maintained_by=maintained_by, created=created, last_modified=last_modified, source=source, status=status))
        counter += 1
        blocks_done += 1
        if counter % COMMIT_COUNT == 0:
            session.commit()
            percent = (blocks_done * NUM_WORKERS * 100) / total_blocks if total_blocks else 0
            logger.debug(f'committed {counter} blocks ({round(time.time() - start_time,2)}s) {percent:.1f}% done')
            counter = 0
            start_time = time.time()
    session.commit()
    session.close()
    logger.debug(f"{current_process().name} finished")

def main(connection_string):
    overall_start_time = time.time()
    setup_connection(connection_string, create_db=True)
    for entry in FILELIST:
        f_name = f"./databases/{entry}"
        if not os.path.exists(f_name):
            logger.info(f"File {f_name} not found")
            continue
        logger.info(f"parsing database file: {f_name}")
        start_time = time.time()
        blocks = read_blocks(f_name)
        logger.info(f"database parsing finished: {round(time.time() - start_time,2)} seconds")
        total_blocks = len(blocks)
        jobs = Queue()
        workers = []
        for _ in range(NUM_WORKERS):
            p = Process(target=parse_blocks, args=(jobs, connection_string, total_blocks), daemon=True)
            p.start()
            workers.append(p)
        for b in blocks:
            jobs.put(b)
        for _ in range(NUM_WORKERS):
            jobs.put(None)
        for p in workers:
            p.join()
        logger.info(f"block parsing finished: {round(time.time() - start_time,2)} seconds")
    logger.info(f"script finished: {round(time.time() - overall_start_time,2)} seconds")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create DB')
    parser.add_argument('-c', dest='connection_string', type=str, required=True, help="Connection string to postgres")
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument('--version', action='version', version=f"%(prog)s {VERSION}")
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    main(args.connection_string)
