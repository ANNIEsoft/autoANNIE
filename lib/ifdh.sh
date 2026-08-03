#!/bin/bash

source /grid/fermiapp/products/common/etc/setups.sh
setup ifdhc

exec ifdh "$@"
