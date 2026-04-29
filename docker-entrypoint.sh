#!/bin/bash

/app/download_dumps.sh

/app/create_db.py -c "$DB_CONNECTION"
