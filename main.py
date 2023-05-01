import requests
import json
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta

# Словарь с соответствием FIGI и тикеров
figi_ticker_map = {'BBG004730RP0': 'GAZP'}
headers = {
    "Authorization": "Bearer t.Tilr8w7bJqxFOJUsUqVLS8kNvdrtB3xvFsGw2kRzkKXlfc05081GgQGNDArK02RBYaOqUuulwpB4lAi0XmJqxw"}

# Подключение к базе данных MongoDB
client = MongoClient(
    'mongodb+srv://thealexis95:Suckmydick1204@cluster0.d7rmw.mongodb.net/InvestForecast?retryWrites=true&w=majority')
db = client['InvestForecast']
stock_collection = db['Stock']


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


# Загрузка данных за последние 15 лет (15 раз за год)
for figi, ticker in figi_ticker_map.items():
    for year in range(2008, 2024):
        start_date = datetime(year, 1, 1).strftime('%Y-%m-%dT00:00:00Z')
        end_date = datetime(year + 1, 1, 1).strftime('%Y-%m-%dT00:00:00Z')
        load_stock_data(figi, start_date, end_date)
    print('Done!')
