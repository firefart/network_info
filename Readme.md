# Ripe Database Parser

This script parses the ARIN/APNIC/LACNIC/AfriNIC/RIPE databases into a local PostgreSQL database.
After the parsing finished you can get the infos for any IPv6 or IPv6 by querying the database.

I recommend using the docker setup because it removes the hassle of installing everything manually.

# Docker

You can simply pull the image from Docker Hub and connect it to a local database via
```sh
docker pull ....
docker run --rm ....
```

If you have checked out the GIT repo you can run the script via docker-compose.
I included some binstubs so you don't have to deal with all the docker commands.

If you run
```sh
./bin/ripe
```
the image will be built, a postgres database is connected, the files are downloaded and the parsing begins.
The database stays up after the run (you can see it via `docker ps`) so you can connect it to your script.

For a one shot query you can run
```
./bin/query IPv4
```
or
```
./bin/query IPv6
```

Or for a psql prompt
```
./bin/psql
```

# Manual Installation

Installation of needed packages (Example on Ubuntu 16.04):
```sh
apt install postgresql python3 python3-netaddr python3-psycopg2 python3-sqlalchemy
```

- or -

```sh
apt install postgresql python3 python-pip
pip install -r requirements.txt
```

Create PostgreSQL database (Use "ripe" as password):
```sh
sudo -u postgres createuser --pwprompt --createdb ripe
sudo -u postgres createdb --owner=ripe ripe
```

Prior to starting this script you need to download the database dumps by executing:
```sh
./download_dumps.sh
```

After importing you can lookup an IP address like:

```sql
SELECT block.inetnum, block.netname, block.country, block.description, block.maintained_by, block.created, block.last_modified, block.source FROM block WHERE block.inetnum >> '2001:db8::1' ORDER BY block.inetnum DESC;
SELECT block.inetnum, block.netname, block.country, block.description, block.maintained_by, block.created, block.last_modified, block.source FROM block WHERE block.inetnum >> '8.8.8.8' ORDER BY block.inetnum DESC;
```

- or -

```bash
./query_db.sh 192.0.2.1
```
