#!/bin/sh

ps aux | grep bitcoinexchangefh | awk '{print $2}' | xargs kill -KILL
sleep 1
cd /home/ec2-user/junma/BitcoinExchangeFH
nohup bitcoinexchangefh -mysql -mysqldest "bitcoin:bitcoin@172.25.1.210:3306" -mysqlschema bcex -instmts selected.ini &
nohup bitcoinexchangefh -mysql -mysqldest "bitcoin:bitcoin@172.25.1.210:3306" -mysqlschema bcex -instmts hbdm.ini &
nohup bitcoinexchangefh -mysql -mysqldest "bitcoin:bitcoin@172.25.1.210:3306" -mysqlschema bcex -instmts gdax.ini &

 
