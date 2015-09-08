# Ripe Database Parser

This script parses the ripe database into a local postgres database.

Prior to starting this script you need to download the ripe db from the following url and place it in this directory

ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inetnum.gz

After importing you can lookup an ip address like:

`select b.*, c.cidr from block b, cidr c where c.block_id = b.id and c.cidr >> '8.8.8.8';`
