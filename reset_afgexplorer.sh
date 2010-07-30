#!/bin/sh

DBNAME=afg
DBUSER=afg

sudo su postgres -c "dropdb $DBNAME"
sudo su postgres -c "createdb -T template_postgis -O $DBUSER $DBNAME"
sudo su postgres -c "psql $DBNAME $DBUSER < data/afg.sql"
