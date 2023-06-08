from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps

import predict_module

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

client = MongoClient(
    'mongodb+srv://thealexis95:Suckmydick1204@cluster0.d7rmw.mongodb.net/InvestForecast?retryWrites=true&w=majority')
db = client['InvestForecast']
users_collection = db['Users']
stock_info_collection = db['StockInfo']
stock_collection = db['Stock']


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
            object_id = ObjectId(data['user_id'])
            print(data['user_id'])
            current_user = users_collection.find_one({"_id": object_id})
            print(current_user)
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(object_id, *args, **kwargs)

    return decorated


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method='sha256')

    user = {
        "name": data['name'],
        "email": data['email'],
        "password": hashed_password,
        "investment_portfolio": []
    }

    result = users_collection.insert_one(user)

    return jsonify({'message': 'User created successfully!'})


@app.route('/login', methods=['POST'])
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Could not verify'}), 401

    user = users_collection.find_one({"email": auth.username})

    if not user:
        return jsonify({'message': 'Could not verify'}), 401

    if check_password_hash(user['password'], auth.password):
        token = jwt.encode(
            {'user_id': str(user['_id']), 'exp': datetime.utcnow() + timedelta(minutes=60)},
            app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({'token': token, 'user_id': str(user['_id'])})

    return jsonify({'message': 'Could not verify'}), 401


@app.route('/add_stock', methods=['POST'])
@token_required
def add_stock(user_id):
    print(user_id)
    ticker = request.args.get('ticker')
    qty = int(request.args.get('quantity'))
    object_id = ObjectId(user_id)
    current_user = users_collection.find_one({"_id": object_id})
    print(current_user)
    portfolio = current_user['investment_portfolio']
    existing_stock = next((stock for stock in portfolio if stock['ticker'] == ticker), None)

    if existing_stock:
        existing_stock['qty'] += qty
        existing_stock['date_added'] = datetime.now()
    else:
        stock = {
            'ticker': ticker,
            'qty': qty,
            'date_added': datetime.now()
        }
        portfolio.append(stock)

    users_collection.update_one({'_id': current_user['_id']}, {'$set': {'investment_portfolio': portfolio}})

    return jsonify({'message': 'Stock added successfully!'})


def calculate_portfolio_returns(investment_portfolio):
    total_investment = 0
    total_returns = 0

    for stock in investment_portfolio:
        ticker = stock['ticker']
        qty = stock['count']

        stock_info = stock_info_collection.find_one({"ticker": ticker})
        if stock_info:
            last_price = stock_info['lastPrice']
            investment = last_price * qty
            total_investment += investment

            if 'initialPrice' in stock:
                initial_price = stock['initialPrice']
                initial_investment = initial_price * qty
                returns = investment - initial_investment
                total_returns += returns

    if total_investment != 0:
        portfolio_returns = (total_returns / total_investment) * 100
    else:
        portfolio_returns = 0

    return portfolio_returns


@app.route('/portfolio', methods=['GET'])
@token_required
def get_portfolio(user_id):
    current_user = users_collection.find_one({"_id": user_id})
    investment_portfolio = current_user['investment_portfolio']

    total = 0
    stocks = []

    for stock in investment_portfolio:
        ticker = stock['ticker']
        qty = int(stock['qty'])

        stock_info = stock_info_collection.find_one({"ticker": ticker})

        if stock_info:
            name = stock_info['name']
            price_per_one = stock_info['lastPrice']
            stock_total = price_per_one * qty
            total += stock_total
            initialPrice = stock_collection.find_one({"date": stock['date_added']})
            stock_data = {
                "ticker": ticker,
                "name": name,
                "count": qty,
                "pricePerOne": round(price_per_one, 2),
                "total": round(stock_total, 2),
                "initialPrice": round(initialPrice['close'], 2)
            }

            stocks.append(stock_data)

    portfolio_returns = calculate_portfolio_returns(stocks)

    response = {
        "investment_portfolio": {
            "total": round(total, 2),
            "stocks": stocks,
            "returns": round(portfolio_returns, 2)
        }
    }

    return jsonify(response)


@app.route('/stocks', methods=['GET'])
def get_stock_info():
    stock_info = stock_info_collection.find()
    return dumps(stock_info)


@app.route('/stocks/<ticker>', methods=['GET'])
def get_stock_prices(ticker):
    projection = {"_id": 0, "date": 1, "close": 1}
    stock_prices = stock_collection.find({"ticker": ticker}, projection)
    return dumps(stock_prices)


@app.route('/stocks/<ticker>/forecast', methods=['GET'])
def get_stock_forecast(ticker):
    stock_prices = list(stock_collection.find())
    forecast = predict_module.make_forecast(stock_prices)
    response = []
    for entry in forecast:
        response.append({
            "date": entry[0].strftime('%Y-%m-%dT00:00:00Z'),
            "close": entry[2]
        })

    return jsonify(response)


if __name__ == '__main__':
    app.run(host='192.168.1.184', port=5000)
