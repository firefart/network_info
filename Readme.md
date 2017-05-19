# Ripe Database Parser

This script parses the ARIN/APNIC/LACNIC/AfriNIC/RIPE databases into a local PostgreSQL database.

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

Prior to starting this script you need to download the database dumps from the following URLs and place it in this directory:
```sh
wget ftp://ftp.afrinic.net/pub/dbase/afrinic.db.gz

wget ftp://ftp.apnic.net/pub/apnic/whois/apnic.db.inetnum.gz
wget ftp://ftp.apnic.net/pub/apnic/whois/apnic.db.inet6num.gz

wget ftp://ftp.arin.net/pub/rr/arin.db

wget ftp://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest

wget ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inetnum.gz
wget ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inet6num.gz

- or simply -

./download_dumps.sh
```

After importing you can lookup an IP address like:

```sql
SELECT block.inetnum, block.country, block.description FROM block WHERE block.inetnum >> '2001:db8::1' ORDER BY block.inetnum DESC LIMIT 1;
select block.* from block where block.inetnum >> '8.8.8.8';
```

- or simply -

```bash
./query_db.sh 192.0.2.1
```

TO-DO:
* ARIN DB seems to be not very complete
* LACNIC DB is missing owner-info
