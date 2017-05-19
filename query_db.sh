#!/bin/sh

psql -e -q -x -c "SELECT block.inetnum, block.country, block.description FROM block WHERE block.inetnum >> '$1' ORDER BY block.inetnum DESC;" ripe
