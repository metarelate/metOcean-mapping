#!/bin/sh

# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of metOcean-mapping.
#
# metOcean-mapping is free software: you can redistribute it and/or 
# modify it under the terms of the GNU Lesser General Public License 
# as published by the Free Software Foundation, either version 3 of 
# the License, or (at your option) any later version.
#
# metOcean-mapping is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with metOcean-mapping. If not, see <http://www.gnu.org/licenses/>.


# currently based on jena-fuseki-0.2.3
# use ONLY with 'localhost' as this version has no authentication.
#
# '/metocean' is a graph label that becomes part of the SPARQL endpoint query URL
#      e.g. http://127.0.0.1:3030/metocean/query?

PORT=3131

if [ X"$1" = X"start" ]
then
    word=$1
elif [ X"$1" = X"stop" ]
then
    word=$1
else
    echo "Usage: $0 [start|stop]"
    exit 255
fi

if [ "$word" = "start" ]
then
    /usr/bin/nohup $FUSEKI_HOME/fuseki-server --loc=./metocean_store/ --update --port=$PORT /metocean &
fi

if [ "$word" = "stop" ]
then
    EE=`ps -ef | grep 'fuseki-server' | fgrep "port=$PORT" | grep -v grep | awk '{print $2}'`
    if [ X"$EE" != X"" ]
    then
        kill $EE
    else
        echo 'Fuseki server not running.'
    fi
fi
