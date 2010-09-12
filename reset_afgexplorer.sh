#!/bin/sh

DBNAME=afg2
DBUSER=afg2

sudo su postgres -c "dropdb $DBNAME"
sudo su postgres -c "createdb -O $DBUSER $DBNAME"
python manage.py syncdb --noinput
python manage.py import_wikileaks data/afg.csv "2010 July 25"
python manage.py build_solr_schema > schema.xml
echo "Please reset Solr now to reflect the new schema, then press [Enter]"
read foo
python manage.py rebuild_index
