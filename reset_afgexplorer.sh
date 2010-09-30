#!/bin/sh
DBNAME=afg2
DBUSER=afg2
# List pairs of (file, release label) here, eg:.
# FILES='file1 "label one" file2 "label two"'
FILES='data/afg.csv "2010 July 25"'

sudo su postgres -c "dropdb $DBNAME"
sudo su postgres -c "createdb -O $DBUSER $DBNAME"
python manage.py syncdb --noinput
echo "$FILES" | xargs python manage.py import_wikileaks
python manage.py build_solr_schema > schema.xml
echo "Please copy or symlink 'schema.xml' into your Solr conf directory, then reset Solr to reflect the new schema, then press [Enter]"
read foo
python manage.py rebuild_index
