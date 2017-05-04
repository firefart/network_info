# Ripe Database Parser

This script parses the ripe database into a local PostgreSQL database.

Installation of needed packages (Example on Ubuntu 16.04):
```sh
apt install postgresql python3 python3-netaddr python3-psycopg2 python3-sqlalchemy

- or -

apt install postgresql python3 python-pip
pip install -r requirements.txt
```

Create PostgreSQL database (Use "ripe" as password):
```sh
sudo -u postgres createuser --pwprompt --createdb ripe
sudo -u postgres createdb --owner=ripe ripe
```

Prior to starting this script you need to download the ripe db from the following URLs and place it in this directory:
```sh
wget ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inetnum.gz
wget ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inet6num.gz
```




After importing you can lookup an IP address like:

```sql
SELECT block.inetnum, block.country, block.description FROM block WHERE block.inetnum >> '2001:db8::1' ORDER BY block.inetnum DESC LIMIT 1;

- or simply -

./query_ripe_db.sh 192.0.2.1
```
