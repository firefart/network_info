# Network Info Parser

This script parses the ARIN/APNIC/LACNIC/AfriNIC/RIPE databases into a local PostgreSQL database.
After the parsing is finished you can get the infos for any IPv4 or IPv6 by querying the database.

This project was used in analysing some data dumps and cross referencing the IPs with the networks.
It can also be used to easily search for netranges assigned to a company in interest.

I recommend using the docker setup because it removes the hassle of installing everything manually.

Hint: The Database can grow fast so be sure to have enough space. On docker my postgres database uses 4.066GB of space.

# Requirements

- Python3 >= 3.3
- postgresql
- python3-netaddr
- python3-psycopg2
- python3-sqlalchemy

# Docker

You can simply pull the image from Docker Hub and connect it to a local database via

```sh
docker pull firefart/network_info
docker run --rm firefart/network_info -c postgres://user:pass@db:5432/network_info
```

Or cou can connect the docker container to another database container.

```sh
docker run --name network_info_db -e POSTGRES_DB=network_info -e POSTGRES_USER=network_info -e POSTGRES_PASSWORD=network_info -d postgres:9-alpine
docker run --rm --link network_info_db:postgres firefart/network_info -c postgres://user:pass@db:5432/network_info
```

If you have checked out the GIT repo you can run the script via docker-compose.
I included some binstubs so you don't have to deal with all the docker commands.

If you run

```sh
./bin/network_info
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

or -

```sh
apt install postgresql python3 python-pip
pip install -r requirements.txt
```

Create PostgreSQL database (Use "network_info" as password):

```sh
sudo -u postgres createuser --pwprompt --createdb network_info
sudo -u postgres createdb --owner=network_info network_info
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

or -

```bash
./query_db.sh 192.0.2.1
```

# Sample run (docker-compose)

```
$ ./bin/network_info
Creating network "ripe_default" with the default driver
Creating volume "ripe_pg_data" with local driver
Creating ripe_db_1
Downloading afrinic.db.gz...
Connecting to ftp.afrinic.net (196.216.2.24:21)
afrinic.db.gz        100% |****************************************************************************************************************************|  5419k  0:00:00 ETA
Downloading apnic.db.inetnum.gz...
Connecting to ftp.apnic.net (202.12.29.205:21)
apnic.db.inetnum.gz  100% |****************************************************************************************************************************| 37065k  0:00:00 ETA
Downloading apnic.db.inet6num.gz...
Connecting to ftp.apnic.net (202.12.29.205:21)
apnic.db.inet6num.gz 100% |****************************************************************************************************************************|  1113k  0:00:00 ETA
Downloading arin.db...
Connecting to ftp.arin.net (199.71.0.151:21)
arin.db              100% |****************************************************************************************************************************| 12314k  0:00:00 ETA
Downloading delegated-lacnic-extended-latest...
Connecting to ftp.lacnic.net (200.3.14.11:21)
delegated-lacnic-ext 100% |****************************************************************************************************************************|  2161k  0:00:00 ETA
Downloading ripe.db.inetnum.gz...
Connecting to ftp.ripe.net (193.0.6.140:21)
ripe.db.inetnum.gz   100% |****************************************************************************************************************************|   228M  0:00:00 ETA
Downloading ripe.db.inet6num.gz...
Connecting to ftp.ripe.net (193.0.6.140:21)
ripe.db.inet6num.gz  100% |****************************************************************************************************************************| 24589k  0:00:00 ETA
2017-05-20 22:29:38,123 - create_db - INFO     - MainProcess - afrinic.db.gz - parsing database file: ./databases/afrinic.db.gz
2017-05-20 22:29:40,440 - create_db - INFO     - MainProcess - afrinic.db.gz - Got 115692 blocks
2017-05-20 22:29:40,440 - create_db - INFO     - MainProcess - afrinic.db.gz - database parsing finished: 2.32 seconds
2017-05-20 22:29:40,440 - create_db - INFO     - MainProcess - afrinic.db.gz - parsing blocks
2017-05-20 22:29:50,904 - create_db - INFO     - MainProcess - afrinic.db.gz - block parsing finished: 10.46 seconds
2017-05-20 22:29:50,904 - create_db - INFO     - MainProcess - apnic.db.inet6num.gz - parsing database file: ./databases/apnic.db.inet6num.gz
2017-05-20 22:29:52,064 - create_db - INFO     - MainProcess - apnic.db.inet6num.gz - Got 66456 blocks
2017-05-20 22:29:52,070 - create_db - INFO     - MainProcess - apnic.db.inet6num.gz - database parsing finished: 1.17 seconds
2017-05-20 22:29:52,070 - create_db - INFO     - MainProcess - apnic.db.inet6num.gz - parsing blocks
2017-05-20 22:29:58,239 - create_db - INFO     - MainProcess - apnic.db.inet6num.gz - block parsing finished: 6.17 seconds
2017-05-20 22:29:58,239 - create_db - INFO     - MainProcess - apnic.db.inetnum.gz - parsing database file: ./databases/apnic.db.inetnum.gz
2017-05-20 22:30:10,663 - create_db - INFO     - MainProcess - apnic.db.inetnum.gz - Got 988559 blocks
2017-05-20 22:30:10,668 - create_db - INFO     - MainProcess - apnic.db.inetnum.gz - database parsing finished: 12.43 seconds
2017-05-20 22:30:10,668 - create_db - INFO     - MainProcess - apnic.db.inetnum.gz - parsing blocks
2017-05-20 22:31:46,156 - create_db - INFO     - MainProcess - apnic.db.inetnum.gz - block parsing finished: 95.49 seconds
2017-05-20 22:31:46,156 - create_db - INFO     - MainProcess - arin.db - parsing database file: ./databases/arin.db
2017-05-20 22:31:46,439 - create_db - INFO     - MainProcess - arin.db - Got 1084 blocks
2017-05-20 22:31:46,491 - create_db - INFO     - MainProcess - arin.db - database parsing finished: 0.34 seconds
2017-05-20 22:31:46,491 - create_db - INFO     - MainProcess - arin.db - parsing blocks
2017-05-20 22:31:46,647 - create_db - INFO     - MainProcess - arin.db - block parsing finished: 0.16 seconds
2017-05-20 22:31:46,647 - create_db - INFO     - MainProcess - delegated-lacnic-extended-latest - parsing database file: ./databases/delegated-lacnic-extended-latest
2017-05-20 22:31:46,648 - create_db - WARNING  - MainProcess - delegated-lacnic-extended-latest - line does not start with lacnic: 2.3|lacnic|20170519|45916|19870101|20170519|-0300
2017-05-20 22:31:46,648 - create_db - WARNING  - MainProcess - delegated-lacnic-extended-latest - Invalid line: lacnic|*|ipv4|*|13389|summary
2017-05-20 22:31:46,648 - create_db - WARNING  - MainProcess - delegated-lacnic-extended-latest - Invalid line: lacnic|*|ipv6|*|25261|summary
2017-05-20 22:31:46,649 - create_db - WARNING  - MainProcess - delegated-lacnic-extended-latest - Invalid line: lacnic|*|asn|*|7266|summary
2017-05-20 22:31:46,806 - create_db - INFO     - MainProcess - delegated-lacnic-extended-latest - Got 38650 blocks
2017-05-20 22:31:46,806 - create_db - INFO     - MainProcess - delegated-lacnic-extended-latest - database parsing finished: 0.16 seconds
2017-05-20 22:31:46,806 - create_db - INFO     - MainProcess - delegated-lacnic-extended-latest - parsing blocks
2017-05-20 22:31:49,669 - create_db - INFO     - MainProcess - delegated-lacnic-extended-latest - block parsing finished: 2.86 seconds
2017-05-20 22:31:49,669 - create_db - INFO     - MainProcess - ripe.db.inetnum.gz - parsing database file: ./databases/ripe.db.inetnum.gz
2017-05-20 22:33:16,952 - create_db - INFO     - MainProcess - ripe.db.inetnum.gz - Got 4113193 blocks
2017-05-20 22:33:16,953 - create_db - INFO     - MainProcess - ripe.db.inetnum.gz - database parsing finished: 87.28 seconds
2017-05-20 22:33:16,953 - create_db - INFO     - MainProcess - ripe.db.inetnum.gz - parsing blocks
2017-05-20 22:41:05,502 - create_db - INFO     - MainProcess - ripe.db.inetnum.gz - block parsing finished: 468.55 seconds
2017-05-20 22:41:05,502 - create_db - INFO     - MainProcess - ripe.db.inet6num.gz - parsing database file: ./databases/ripe.db.inet6num.gz
2017-05-20 22:41:25,049 - create_db - INFO     - MainProcess - ripe.db.inet6num.gz - Got 995238 blocks
2017-05-20 22:41:25,261 - create_db - INFO     - MainProcess - ripe.db.inet6num.gz - database parsing finished: 19.76 seconds
2017-05-20 22:41:25,261 - create_db - INFO     - MainProcess - ripe.db.inet6num.gz - parsing blocks
2017-05-20 22:43:11,061 - create_db - INFO     - MainProcess - ripe.db.inet6num.gz - block parsing finished: 105.8 seconds
2017-05-20 22:43:11,061 - create_db - INFO     - MainProcess - empty - script finished: 813.01 seconds

$ ./bin/query 176.28.20.159
SELECT block.inetnum, block.netname, block.country, block.description, block.maintained_by, block.created, block.last_modified, block.source FROM block WHERE block.inetnum >> '176.28.20.159' ORDER BY block.inetnum DESC;
-[ RECORD 1 ]-+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
inetnum       | 176.28.16.0/21
netname       | DE-HE-LVPS-176-28-16-NET
country       | DE
description   | Hosteurope GmbH
maintained_by | MNT-HEG-MASS
created       | 2011-08-30 12:34:13
last_modified | 2015-12-01 15:01:32
source        | ripe
-[ RECORD 2 ]-+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
inetnum       | 176.28.0.0/18
netname       | DE-HEG-20110520
country       | DE
description   |
maintained_by | RIPE-NCC-HM-MNT MNT-HEG
created       | 2011-05-20 05:51:39
last_modified | 2016-07-22 06:43:13
source        | ripe
-[ RECORD 3 ]-+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
inetnum       | 176.0.0.0/8
netname       | EU-ZZ-176
country       | EU # Country is in fact world wide
description   | To determine the registration information for a more specific range, please try a more specific query. If you see this object as a result of a single IP query, it means the IP address is currently in the free pool of address space managed by the RIPE NCC.
maintained_by | RIPE-NCC-HM-MNT
created       | 2010-05-10 11:10:14
last_modified | 2015-09-23 13:18:28
source        | ripe
-[ RECORD 4 ]-+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
inetnum       | 176.0.0.0/8
netname       | IANA-NETBLOCK-176
country       | AU
description   | This network range is not allocated to APNIC. If your whois search has returned this message, then you have searched the APNIC whois database for an address that is allocated by another Regional Internet Registry (RIR). Please search the other RIRs at whois.arin.net or whois.ripe.net for more information about that range.
maintained_by | MAINT-APNIC-AP
created       |
last_modified |
source        | apnic
-[ RECORD 5 ]-+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
inetnum       | 0.0.0.0/0
netname       | IANA-BLK
country       | EU # Country field is actually all countries in the world and not just EU countries
description   | The whole IPv4 address space
maintained_by | RIPE-NCC-HM-MNT
created       | 2002-06-25 14:19:09
last_modified | 2012-02-08 09:09:31
source        | ripe
-[ RECORD 6 ]-+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
inetnum       | 0.0.0.0/0
netname       | IANA-BLOCK
country       | AU
description   | General placeholder reference for all IPv4 addresses
maintained_by | MAINT-APNIC-AP
created       |
last_modified |
source        | apnic
-[ RECORD 7 ]-+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
inetnum       | 0.0.0.0/0
netname       | IANA-BLK
country       | EU # Country is really world wide
description   | The whole IPv4 address space
maintained_by | AFRINIC-HM-MNT
created       |
last_modified |
source        | afrinic
```
