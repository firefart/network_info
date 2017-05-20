#!/bin/sh

psql -e -q -x -c "SELECT block.inetnum, block.netname, block.country, block.description, block.maintained_by, block.created, block.last_modified, block.source FROM block WHERE block.inetnum >> '$1' ORDER BY block.inetnum DESC;" ripe
