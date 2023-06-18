import requests
import database_interaction as db
from pymongo import MongoClient
from datetime import datetime, timedelta

# Словарь с соответствием FIGI и тикеров
figi_ticker_map = {'BBG004731489': 'GMKN', 'BBG004S683W7': 'AFLT', 'BBG004730RP0': 'GAZP'}
headers = {
    "Authorization": "Bearer t.Tilr8w7bJqxFOJUsUqVLS8kNvdrtB3xvFsGw2kRzkKXlfc05081GgQGNDArK02RBYaOqUuulwpB4lAi0XmJqxw"}


def load_stock_data(figi, ticker, start_date, end_date):
    url = f'https://api-invest.tinkoff.ru/openapi/market/candles?figi={figi}&from={start_date}&to={end_date}&interval=day'
    response = requests.get(url, headers=headers)
    data = response.json()['payload']['candles']
    for item in data:
        open_price = item['o']
        high_price = item['h']
        low_price = item['l']
        close_price = item['c']
        volume = item['v']
        date = datetime.fromisoformat(item['time'][:10])

        share_id = db.get_share_id(ticker)
        if share_id is None:
            name = get_share_info_from_tinkoff(ticker)
            if name is not None:
                db.insert_share_info(ticker, name, close_price)
                share_id = db.get_share_id(ticker)
                db.insert_stock_price(share_id, date, open_price, high_price, low_price, close_price, volume)

        if share_id is not None:
            db.insert_stock_price(share_id, date, open_price, high_price, low_price, close_price, volume)


def load_new_stock():
    for figi, ticker in figi_ticker_map.items():
        print(figi)
        for year in range(2008, 2024):
            start_date = datetime(year, 1, 1).strftime('%Y-%m-%dT00:00:00Z')
            end_date = datetime(year + 1, 1, 1).strftime('%Y-%m-%dT00:00:00Z')

            load_stock_data(figi, ticker, start_date, end_date)
        print('Done!')


def get_share_info_from_tinkoff(ticker):
    url = f'https://api-invest.tinkoff.ru/openapi/market/search/by-ticker?ticker={ticker}'
    response = requests.get(url, headers=headers)
    data = response.json()['payload']['instruments']
    if len(data) > 0:
        instrument = data[0]
        name = instrument['name']
        return name
    return None


def update_share_info(ticker):
    share = db.get_share_by_ticker(ticker)
    last_price = db.get_last_stock_price(share[0])
    print(last_price)
    db.update_share_price(ticker, last_price)


load_new_stock()
for ticker in figi_ticker_map.values():
    update_share_info(ticker)
