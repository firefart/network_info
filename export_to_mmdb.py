#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import gc
from datetime import datetime
import netaddr
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from db.model import Block
from db.helper import create_postgres_pool


def export_to_mmdb(connection_string, output_file, table="block"):
    """Export PostgreSQL table to MMDB format"""
    
    # Create database connection
    engine = create_postgres_pool(connection_string)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Query all blocks with streaming to avoid memory issues
    print(f"Exporting table '{table}' to MMDB format...")
    query = select(Block)
    result = session.execute(query)
    
    # Use yield_per to stream blocks instead of loading all at once
    blocks = result.scalars().yield_per(1000)
    
    print(f"Starting export (streaming blocks)...")
    
    try:
        from mmdb_writer import MMDBWriter
    except ImportError:
        print("Error: mmdb_writer library not found. Please install it with: pip install mmdb-writer")
        sys.exit(1)
    
    writer = MMDBWriter(
        ip_version=6,
        ipv4_compatible=True,
        database_type="Network Info Block",
        languages=["en"],
        description={
            "en": "Network block information from RIR databases"
        },
    )
    
    count = 0
    
    for block in blocks:
        try:
            # Skip default route blocks that aren't real networks
            cidr = str(block.inetnum)
            if cidr in ['::/0', '0.0.0.0/0']:
                continue
            
            # Create the data structure for this network - minimize memory usage
            data = {
                "netname": block.netname or "",
                "country": block.country or "",
                "description": block.description or "",
                "maintained_by": block.maintained_by or "",
                "created": block.created.strftime('%Y-%m-%d') if block.created else "",
                "last_modified": block.last_modified.strftime('%Y-%m-%d') if block.last_modified else "",
                "source": block.source or "",
                "status": block.status or ""
            }
            
            # Insert network using IPSet with CIDR string list
            ipset = netaddr.IPSet([cidr])
            writer.insert_network(ipset, data)
            count += 1
            
            if count % 10000 == 0:
                print(f"  Processed {count} blocks...")
                # Force garbage collection periodically
                gc.collect()
            
        except Exception as e:
            print(f"Warning: Failed to process block {block.inetnum}: {e}")
            continue
    
    # Write to file
    writer.to_db_file(output_file)
    print(f"Export completed successfully: {count} blocks -> {output_file}")
    
    session.close()


def main():
    parser = argparse.ArgumentParser(description="Export PostgreSQL table to MMDB format")
    parser.add_argument("-c", "--connection", 
                        default="postgresql://network_info:network_info@db:5432/network_info",
                        help="Database connection string")
    parser.add_argument("-o", "--output",
                        default="block_dump.mmdb",
                        help="Output MMDB file path")
    parser.add_argument("-t", "--table",
                        default="block",
                        help="Table name to export")
        
    args = parser.parse_args()
    
    # Add date to output filename if not already present
    if "_$(date" not in args.output and not args.output.endswith(".mmdb"):
        args.output = f"{args.output}_{datetime.now().strftime('%Y-%m-%d')}.mmdb"
    elif not args.output.endswith(".mmdb"):
        args_output = args.output.rsplit(".", 1)[0]
        args.output = f"{args_output}_{datetime.now().strftime('%Y-%m-%d')}.mmdb"
    
    export_to_mmdb(args.connection, args.output, args.table)


if __name__ == "__main__":
    main()
