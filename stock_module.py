import requests
import json
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta

# Словарь с соответствием FIGI и тикеров
figi_ticker_map = {'BBG004730RP0': 'GAZP', 'BBG004S683W7': 'AFLT'}
headers = {
    "Authorization": "Bearer t.Tilr8w7bJqxFOJUsUqVLS8kNvdrtB3xvFsGw2kRzkKXlfc05081GgQGNDArK02RBYaOqUuulwpB4lAi0XmJqxw"}

# Подключение к базе данных MongoDB
client = MongoClient(
    'mongodb+srv://thealexis95:Suckmydick1204@cluster0.d7rmw.mongodb.net/InvestForecast?retryWrites=true&w=majority')
db = client['InvestForecast']
stock_collection = db['Stock']
stock_info_collection = db['StockInfo']


# Функция для загрузки данных по тикеру за определенный временной промежуток
def load_stock_data(figi, start_date, end_date):
    url = f'https://api-invest.tinkoff.ru/openapi/market/candles?figi={figi}&from={start_date}&to={end_date}&interval=day'
    response = requests.get(url, headers=headers)
    data = response.json()['payload']['candles']
    stocks = []
    for item in data:
        stock = {
            'ticker': figi_ticker_map[figi],
            'date': datetime.fromisoformat(item['time'][:10]),
            'open': item['o'],
            'high': item['h'],
            'low': item['l'],
            'close': item['c'],
            'volume': item['v']
        }
        stocks.append(stock)
    stock_collection.insert_many(stocks)


def load_new_stock():
    # Загрузка данных за последние 15 лет (15 раз за год)
    for figi, ticker in figi_ticker_map.items():
        for year in range(2008, 2024):
            start_date = datetime(year, 1, 1).strftime('%Y-%m-%dT00:00:00Z')
            end_date = datetime(year + 1, 1, 1).strftime('%Y-%m-%dT00:00:00Z')
            load_stock_data(figi, start_date, end_date)
        print('Done!')


def get_last_data_date():
    last_record = stock_collection.find().sort('date', -1).limit(1).next()
    last_date = last_record['date']

    return last_date


def update_stock_data(figi):
    today = datetime.utcnow().date()
    last_data_date = get_last_data_date()  # Получаем последнюю дату информации о цене из базы данных или другого источника
    if last_data_date is None:
        start_date = today - timedelta(days=1)
    else:
        start_date = last_data_date + timedelta(days=1)
    end_date = today
    print(last_data_date)
    print(start_date)
    formatted_start_date = start_date.strftime('%Y-%m-%dT00:00:00Z')
    formatted_end_date = end_date.strftime('%Y-%m-%dT00:00:00Z')
    load_stock_data(figi, formatted_start_date, formatted_end_date)


def get_stock_info_from_tinkoff(ticker):
    url = f'https://api-invest.tinkoff.ru/openapi/market/search/by-ticker?ticker={ticker}'
    response = requests.get(url, headers=headers)
    data = response.json()['payload']['instruments']
    if len(data) > 0:
        instrument = data[0]
        name = instrument['name']
        return name
    return None


def update_stock_data_from_db():
    stocks = stock_collection.find().sort('date', -1)  # Сортировка по дате в обратном порядке
    for stock in stocks:
        ticker = stock['ticker']
        last_price = stock['close']

        stock_info = stock_info_collection.find_one({'ticker': ticker})
        if stock_info is None:
            name = get_stock_info_from_tinkoff(ticker)
            if name is not None:
                stock_info_collection.insert_one({'ticker': ticker, 'name': name, 'lastPrice': last_price})
        else:
            stock_info_collection.update_one(
                {'_id': stock_info['_id']},
                {'$set': {'lastPrice': last_price}}
            )
            break  # Прерываем цикл после обновления первой записи


def add_stock_info():
    tickers = stock_collection.distinct('ticker')
    for ticker in tickers:
        last_record = stock_collection.find({'ticker': ticker}).sort('date', -1).limit(1).next()
        last_price = last_record['close']

        stock_info = stock_info_collection.find_one({'ticker': ticker})
        if stock_info is None:
            name = get_stock_info_from_tinkoff(ticker)
            if name is not None:
                stock_info_collection.insert_one({'ticker': ticker, 'name': name, 'lastPrice': last_price})
        else:
            stock_info_collection.update_one(
                {'_id': stock_info['_id']},
                {'$set': {'lastPrice': last_price}}
            )


add_stock_info()
