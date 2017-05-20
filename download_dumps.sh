#!/bin/sh

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
DOWNLOAD_DIR="$DIR/databases"
mkdir -p $DOWNLOAD_DIR

function download {
  name=$(echo $1 |awk -F "/" '{print $NF}')
  echo "Downloading $name..."
  wget -O "$DOWNLOAD_DIR/$name" "$1"
}

download "ftp://ftp.afrinic.net/pub/dbase/afrinic.db.gz"

download "ftp://ftp.apnic.net/pub/apnic/whois/apnic.db.inetnum.gz"
download "ftp://ftp.apnic.net/pub/apnic/whois/apnic.db.inet6num.gz"

download "ftp://ftp.arin.net/pub/rr/arin.db"

download "ftp://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest"

download "ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inetnum.gz"
download "ftp://ftp.ripe.net/ripe/dbase/split/ripe.db.inet6num.gz"
