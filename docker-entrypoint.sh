#!/bin/bash

./download_dumps.sh

/app/create_db.py "$@"
