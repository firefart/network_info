#!/bin/sh

psql -q -A -t -c "SELECT block.inetnum, block.country, block.description FROM block WHERE block.inetnum >> '$1' ORDER BY block.inetnum DESC LIMIT 1;" ripe
