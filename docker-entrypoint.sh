#!/bin/bash

./download_dumps.sh

/ripe/create_db.py "$@"
