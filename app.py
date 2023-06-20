import json

import pandas as pd
from flask import Flask, request, jsonify
from bson.json_util import dumps
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta, date
from functools import wraps

import predict_module
import database_interaction as database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'


# Декоратор для проверки наличия токена
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            user_id = int(data['user_id'])
            current_user = database.get_user_by_id(user_id)
            print(current_user)
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(user_id, *args, **kwargs)

    return decorated


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method='sha256')

    user = {
        "name": data['name'],
        "lastname": data['lastname'],
        "email": data['email'],
        "password": hashed_password,
    }

    user_id = database.add_user(user)

    return jsonify({'message': 'User created successfully!'})


@app.route('/login', methods=['POST'])
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Could not verify'}), 401

    user = database.get_user_by_email(auth.username)
    print(user)
    if not user:
        return jsonify({'message': 'Could not verify'}), 401

    if check_password_hash(user[3], auth.password):
        token = jwt.encode(
            {'user_id': str(user[0]), 'exp': datetime.utcnow() + timedelta(minutes=60)},
            app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({'token': token, 'user_id': str(user[0])})

    return jsonify({'message': 'Could not verify'}), 401


@app.route('/add_stock', methods=['POST'])
@token_required
def add_stock(user_id):
    ticker = request.args.get('ticker')
    qty = int(request.args.get('quantity'))

    stock_info = database.get_stock_info_by_ticker(ticker)

    # Добавление акций в таблицу usershares
    share_id = database.get_share_id(ticker)
    purchase_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database.insert_share_to_portfolio(user_id, share_id, qty, stock_info[3], purchase_date)

    return jsonify({'message': 'Stock added successfully!'})


@app.route('/portfolio', methods=['GET'])
@token_required
def get_portfolio(user_id):
    start_date = "2022-06-18"
    end_date = "2023-06-19"

    # Получение данных о портфеле (название, тикер, цена и количество акций)
    percentage_return, monetary_return = predict_module.calculate_dietz_return(user_id, start_date, end_date)

    # Получение данных о портфеле (название, тикер, цена и количество акций)
    portfolio_data = database.get_users_shares(user_id)  # Замените на свою функцию для получения данных портфеля

    # Создание словаря для объединения акций по тикеру
    stocks = {}

    for stock in portfolio_data:
        shareinfo = database.get_share_by_id(stock[2])
        ticker = shareinfo[1]
        if ticker in stocks:
            # Если акция с таким тикером уже существует в портфеле, обновляем информацию
            stocks[ticker]['count'] += stock[3]
            stocks[ticker]['total'] += stock[3] * shareinfo[3]
        else:
            # Если акции с таким тикером нет в портфеле, добавляем ее
            stocks[ticker] = {
                "count": stock[3],
                "name": shareinfo[2],
                "pricePerOne": shareinfo[3],
                "ticker": ticker,
                "total": stock[3] * shareinfo[3]
            }

    total_value = sum(stock['total'] for stock in stocks.values())
    response = {
        "investment_portfolio": {
            "returns": {
                "percentage_return": percentage_return,
                "monetary_return": monetary_return
            },
            "stocks": list(stocks.values()),
            "total": total_value
        }
    }

    return jsonify(response)


@app.route('/stocks', methods=['GET'])
def get_stock_info():
    stock_info = database.get_stock_info()
    response = []
    for stock in stock_info:
        data = {
            "id": stock[0],
            "ticker": stock[1],
            "name": stock[2],
            "lastPrice": stock[3]
        }
        response.append(data)
    print(stock_info)
    return dumps(response)


@app.route('/stocks/<ticker>', methods=['GET'])
def get_stock_prices(ticker):
    share = database.get_share_by_ticker(ticker)
    stock_prices = database.get_stock_prices(share[0])
    response = []
    for stock in stock_prices:
        data = {
            "date": stock[0],
            "open": stock[1],
            "high": stock[2],
            "low": stock[3],
            "close": stock[4],
            "volume": stock[5],
        }
        response.append(data)
    return dumps(response, default=str)


@app.route('/stocks/<ticker>/forecast', methods=['GET'])
def get_stock_forecast(ticker):
    share = database.get_share_by_ticker(ticker)
    stock_prices = list(database.get_stock_prices(share[0]))
    df = make_df(stock_prices)
    prophet = predict_module.Prophet_Prediction(df, 30)
    lin_reg = predict_module.LinReg_Prediction(df, 30)
    rnn = predict_module.RNN_LSTM_Prediction(df, 30)
    prophet_forecast = prophet.forecast()
    linreg_forecast = lin_reg.forecast(30)
    rnn_forecast = rnn.forecast()
    #forecast = predict_module.make_forecast(stock_prices)
    response = []
    print(prophet_forecast)
    print(linreg_forecast)
    print(rnn_forecast)
    prophet_data = [{'date': date.strftime('%Y-%m-%d'), 'close': close} for date, close in
                    zip(prophet_forecast.index, prophet_forecast['close'])]
    linreg_data = [{'date': date.strftime('%Y-%m-%d %H:%M:%S'), 'close': close} for date, close in
                   zip(linreg_forecast.index, linreg_forecast['forecast'])]
    rnn_data = [{'date': date.strftime('%Y-%m-%d %H:%M:%S'), 'close': close[0]} for date, close in zip(pd.to_datetime(rnn_forecast.index), rnn_forecast.values)]
    response = {
        'prophet': prophet_data,
        'linreg': linreg_data,
        'rnn': rnn_data
    }

    return json.dumps(response)

def make_df(stock_prices):
    df = pd.DataFrame(stock_prices)
    # Переименование столбцов
    df.rename(columns={0: 'date', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
    if 'date' in df:
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    print(df)
    df.set_index('date', inplace=True)
    return df


if __name__ == '__main__':
    app.run(host='192.168.1.184', port=5000)
