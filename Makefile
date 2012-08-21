
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



DRAFT=$(wildcard draft/*)
DEFAULT=$(wildcard default/*)
STORE=$(wildcard metocean_store/*)

all: load start

.PHONY: force

load: clean
	@#$$JENAROOT/bin/tdbloader --graph=http://draft --loc="./metocean_store/" $(DRAFT)
	@for i in $(DRAFT); \
	do \
		$$JENAROOT/bin/tdbloader --graph=http://$$i --loc="./metocean_store/" $$i ;\
	done
	# now load the default data into the default (unnamed) graph
	$$JENAROOT/bin/tdbloader --loc="./metocean_store/" $(DEFAULT)

start: 
	./run_fuseki.sh start

stop: 
	./run_fuseki.sh stop

clean: stop dump
	rm -f nohup.out
	rm -f $(STORE)

dump:
	$$JENAROOT/bin/tdbdump --loc="./metocean_store/" |\
		 xz -9c > tdbdump.metocean_store.`date +'%F_%T'`.xz


