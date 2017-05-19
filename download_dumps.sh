#!/bin/sh

mkdir -p ./databases

wget ftp://ftp.afrinic.net/pub/dbase/afrinic.db.gz

wget ftp://ftp.apnic.net/pub/apnic/whois/apnic.db.inetnum.gz
wget ftp://ftp.apnic.net/pub/apnic/whois/apnic.db.inet6num.gz

wget ftp://ftp.arin.net/pub/rr/arin.db

wget ftp://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest

wget ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inetnum.gz
wget ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inet6num.gz
