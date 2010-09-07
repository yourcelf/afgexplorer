#!/bin/sh

DBNAME=afg2
DBUSER=afg2

sudo su postgres -c "dropdb $DBNAME"
sudo su postgres -c "createdb -T template_postgis -O $DBUSER $DBNAME"
python manage.py syncdb --noinput
#sudo su postgres -c "psql $DBNAME $DBUSER < data/afg.sql"
