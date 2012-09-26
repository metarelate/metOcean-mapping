#!/bin/bash

export metOcean="."

$JENAROOT/bin/tdbquery --loc=$metOcean/metocean_store --query=saveCacheQuery.qu > $metOcean/default/zzztmp.ttl

mdOut=$(md5sum $metOcean/default/zzztmp.ttl) 

md=$(echo $mdOut | cut -d' ' -f1)

mv ${metOcean}/default/zzztmp.ttl ${metOcean}/default/${md}.ttl

