#!/bin/sh

cd /home/ec2-user/junma/BitcoinExchangeFH;nohup bitcoinexchangefh -mysql -mysqldest "bitcoin:bitcoin@172.25.1.210:3306" -mysqlschema bcex -instmts selected.ini &

