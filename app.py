from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import stock_module
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

client = MongoClient(
    'mongodb+srv://thealexis95:Suckmydick1204@cluster0.d7rmw.mongodb.net/InvestForecast?retryWrites=true&w=majority')
db = client['InvestForecast']
users_collection = db['Users']


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
            {'user_id': str(user['_id']), 'exp': datetime.utcnow() + datetime.timedelta(minutes=30)},
            app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({'token': token, 'user_id': str(user['_id'])})

    return jsonify({'message': 'Could not verify'}), 401


@app.route('/add_stock', methods=['POST'])
@token_required
def add_stock(user_id):
    print(user_id)
    data = request.get_json()
    ticker = data['ticker']
    qty = data['qty']
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


@app.route('/portfolio', methods=['GET'])
@token_required
def get_portfolio(user_id):
    current_user = users_collection.find_one({"_id": user_id})
    investment_portfolio = current_user['investment_portfolio']
    return dumps(investment_portfolio)


if __name__ == '__main__':
    app.run()
