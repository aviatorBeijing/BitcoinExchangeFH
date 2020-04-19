#!/bin/sh
python3 befh/bitcoinexchangefh.py -pg -pgdest "root:iceball12345@localhost:5432" -pgschema befh -instmts gdax.ini
