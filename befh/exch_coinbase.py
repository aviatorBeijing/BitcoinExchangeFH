'''
Created on Nov 29, 2018

@author: junma
'''

from befh.ws_api_socket import WebSocketApiClient
from befh.market_data import L2Depth, Trade
from befh.exchange import ExchangeGateway
from befh.instrument import Instrument
from befh.sql_client_template import SqlClientTemplate
from befh.util import Logger
import time
import threading
import json
from functools import partial
from datetime import datetime

DEBUG=True

class ExchGwApiCoinbase(WebSocketApiClient):
    """
    Exchange socket
    """
    def __init__(self):
        """
        Constructor
        """
        WebSocketApiClient.__init__(self, 'Coinbase')
        
    @classmethod
    def get_trades_timestamp_field_name(cls):
        return 'time'
    
    @classmethod
    def get_bids_field_name(cls):
        return 'bids'
        
    @classmethod
    def get_asks_field_name(cls):
        return 'asks'
        
    @classmethod
    def get_trade_side_field_name(cls):
        return 'side'
        
    @classmethod
    def get_trade_id_field_name(cls):
        return 'trade_id'
        
    @classmethod
    def get_trade_price_field_name(cls):
        return 'price'        
        
    @classmethod
    def get_trade_volume_field_name(cls):
        return 'last_size'   
        
    @classmethod
    def get_link(cls):
        return 'wss://ws-feed.pro.coinbase.com'

    @classmethod
    def get_order_book_subscription_string(cls, instmt):
        if cls.is_default_instmt(instmt):
            return json.dumps({"type":"subscribe","product_id":'BTC-USD',
                               "channels":[{"name":"l2update","product_ids":["BTC-USD"]}]
                               })
        else:
            return json.dumps({"type":"subscribe","product_id":instmt.get_instmt_code(),
                               "channels":[{"name":"l2update","product_ids":[instmt.get_instmt_code()]}]
                               })

    @classmethod
    def get_trades_subscription_string(cls, instmt):
        if cls.is_default_instmt(instmt):
            return json.dumps({"type":"subscribe",
                               "product_ids": ["BTC-USD"],
                               "channels":[
                                   "heartbeat",
                                   {"name":"ticker", "product_ids":[ "BTC-USD" ] }
                                   ]})
        else:
            return json.dumps({"type":"subscribe",
                               "product_ids": [ instmt.get_instmt_code() ],
                               "channels":[
                                   "heartbeat",
                                   {"name":"ticker", "product_ids":[ instmt.get_instmt_code() ] }
                                   ]})
 
    @classmethod
    def is_default_instmt(cls, instmt):
        return instmt.get_instmt_code() == "\"\"" or instmt.get_instmt_code() == "" or instmt.get_instmt_code() == "''"
            
    @classmethod
    def parse_l2_depth(cls, instmt, raw):
        """
        Parse raw data to L2 depth
        :param instmt: Instrument
        :param raw: Raw data in JSON
        """
        l2_depth = instmt.get_l2_depth()
        keys = list(raw.keys())
        if cls.get_bids_field_name() in keys and \
           cls.get_asks_field_name() in keys:
            
            # Date time
            l2_depth.date_time = datetime.utcnow().strftime("%Y%m%d %H:%M:%S.%f")
            
            # Bids
            bids = raw[cls.get_bids_field_name()]
            bids_len = min(l2_depth.depth, len(bids))
            for i in range(0, bids_len):
                l2_depth.bids[i].price = float(bids[i][0]) if type(bids[i][0]) != float else bids[i][0]
                l2_depth.bids[i].volume = float(bids[i][1]) if type(bids[i][1]) != float else bids[i][1]   

            # Asks
            asks = raw[cls.get_asks_field_name()]
            asks_len = min(l2_depth.depth, len(asks))
            for i in range(0, asks_len):
                l2_depth.asks[i].price = float(asks[i][0]) if type(asks[i][0]) != float else asks[i][0]
                l2_depth.asks[i].volume = float(asks[i][1]) if type(asks[i][1]) != float else asks[i][1]            
        else:
            raise Exception('Does not contain order book keys in instmt %s-%s.\nOriginal:\n%s' % \
                (instmt.get_exchange_name(), instmt.get_instmt_name(), \
                 raw))
        
        return l2_depth        

    @classmethod
    def parse_trade(cls, instmt, raw):
        """
        :param instmt: Instrument
        :param raw: Raw data in JSON
        :return:
        """
        trade = Trade()
        keys = list(raw.keys())

        if cls.get_trades_timestamp_field_name() in keys and \
           cls.get_trade_id_field_name() in keys and \
           cls.get_trade_side_field_name() in keys and \
           cls.get_trade_price_field_name() in keys and \
           cls.get_trade_volume_field_name() in keys:
        
            # Date time
            date_time = raw[cls.get_trades_timestamp_field_name()]
            trade.date_time = datetime.strptime(date_time,"%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y%m%d %H:%M:%S.%f")            
            
            # Trade side
            # Buy = 0
            # Side = 1
            trade.trade_side = Trade.parse_side(raw[cls.get_trade_side_field_name()])
                
            # Trade id
            trade.trade_id = str(raw[cls.get_trade_id_field_name()])
            
            # Trade price
            trade.trade_price = raw[cls.get_trade_price_field_name()]            
            
            # Trade volume
            trade.trade_volume = raw[cls.get_trade_volume_field_name()]                        
        else:
            raise Exception('Does not contain trade keys in instmt %s-%s.\nOriginal:\n%s' % \
                (instmt.get_exchange_name(), instmt.get_instmt_name(), \
                 raw))        

        return trade        


class ExchGwCoinbase(ExchangeGateway):
    """
    Exchange gateway
    """
    def __init__(self, db_clients):
        """
        Constructor
        :param db_client: Database client
        """
        ExchangeGateway.__init__(self, ExchGwApiCoinbase(), db_clients)

    @classmethod
    def get_exchange_name(cls):
        """
        Get exchange name
        :return: Exchange name string
        """
        return 'Coinbase'

    def on_open_handler(self, instmt, ws):
        """
        Socket on open handler
        :param instmt: Instrument
        :param ws: Web socket
        """
        Logger.info(self.__class__.__name__, "Instrument %s is subscribed in channel %s" % \
                  (instmt.get_instmt_name(), instmt.get_exchange_name()))
        if not instmt.get_subscribed():
            if DEBUG: 
                print( self.api_socket.get_order_book_subscription_string(instmt) )
                print( self.api_socket.get_trades_subscription_string(instmt) )
            ws.send(self.api_socket.get_order_book_subscription_string(instmt))
            ws.send(self.api_socket.get_trades_subscription_string(instmt))            
            instmt.set_subscribed(True)

    def on_close_handler(self, instmt, ws):
        """
        Socket on close handler
        :param instmt: Instrument
        :param ws: Web socket
        """
        Logger.info(self.__class__.__name__, "Instrument %s is unsubscribed in channel %s" % \
                  (instmt.get_instmt_name(), instmt.get_exchange_name()))
        instmt.set_subscribed(False)

    def on_message_handler(self, instmt, message):
        """
        Incoming message handler
        :param instmt: Instrument
        :param message: Message
        """
        keys = message.keys()
        if DEBUG:
            print( message )
            for k,v in message.items():
                print("\t", k,"::", v)
        
        if 'type' in keys and message['type'] in ['ticker'] and all( [s in keys for s in ['product_id','price','time']] ):
            channel_name = message['type']
            if (self.api_socket.is_default_instmt(instmt) and channel_name == "order_book") or \
               (not self.api_socket.is_default_instmt(instmt) and channel_name == "order_book_%s" % instmt.get_instmt_code()):
                instmt.set_prev_l2_depth(instmt.get_l2_depth().copy())
                self.api_socket.parse_l2_depth(instmt, json.loads(message['data']))
                if instmt.get_l2_depth().is_diff(instmt.get_prev_l2_depth()):
                    instmt.incr_order_book_id()
                    if not DEBUG:
                        self.insert_order_book(instmt)
                    else:
                        print( instmt )
            elif channel_name == "ticker" and 'time' in keys:
                trade = self.api_socket.parse_trade(instmt, message)
                if trade.trade_id != instmt.get_exch_trade_id():
                    instmt.incr_trade_id()
                    instmt.set_exch_trade_id(trade.trade_id)
                    if not DEBUG:
                        self.insert_trade(instmt, trade)
                    else:
                        print( instmt )
                        print( trade )  

    def start(self, instmt):
        """
        Start the exchange gateway
        :param instmt: Instrument
        :return List of threads
        """
        instmt.set_l2_depth(L2Depth(20))
        instmt.set_prev_l2_depth(L2Depth(20))
        instmt.set_instmt_snapshot_table_name(self.get_instmt_snapshot_table_name(instmt.get_exchange_name(),
                                                                                  instmt.get_instmt_name()))
        self.init_instmt_snapshot_table(instmt)
        return [self.api_socket.connect(self.api_socket.get_link(),
                                        on_message_handler=partial(self.on_message_handler, instmt),
                                        on_open_handler=partial(self.on_open_handler, instmt),
                                        on_close_handler=partial(self.on_close_handler, instmt))]
                                        

if __name__ == '__main__':
    exchange_name = 'Coinbase'
    instmt_name = 'ETH-USD'
    instmt_code = 'ETH-USD'
    instmt = Instrument(exchange_name, instmt_name, instmt_code)
    db_client = SqlClientTemplate()
    Logger.init_log()
    exch = ExchGwCoinbase([db_client])
    td = exch.start(instmt)

