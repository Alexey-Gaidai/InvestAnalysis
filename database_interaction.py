import mysql.connector
from mysql.connector import pooling

# Создание пула соединений
connection_pool = pooling.MySQLConnectionPool(
    pool_name="my_connection_pool",
    pool_size=5,
    host="localhost",
    user="root",
    password="Lehas",
    database="invest_db"
)


# Функция для получения соединения из пула
def get_connection():
    return connection_pool.get_connection()


# Функция для освобождения соединения и его возврата в пул
def release_connection(connection):
    connection.close()


# Функция для получения пользователя по идентификатору
def get_user_by_id(user_id):
    connection = get_connection()
    try:
        with connection.cursor(buffered=True) as cursor:
            query = "SELECT * FROM Users WHERE id = %s"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result
    finally:
        release_connection(connection)


# Функция для получения пользователя по адресу электронной почты
def get_user_by_email(email):
    connection = get_connection()
    try:
        with connection.cursor(buffered=True) as cursor:
            query = "SELECT * FROM userlogin WHERE email = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()
            return result
    finally:
        release_connection(connection)


def insert_share_info(ticker, name, actual_price):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO shareinfo (ticker, name, actualPrice) VALUES (%s, %s, %s)"
            values = (ticker, name, actual_price)
            cursor.execute(query, values)
        connection.commit()
    finally:
        release_connection(connection)


def get_share_id(ticker):
    connection = get_connection()
    try:
        with connection.cursor(buffered=True) as cursor:
            query = "SELECT id FROM ShareInfo WHERE ticker = %s"
            cursor.execute(query, (ticker,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
    finally:
        release_connection(connection)


def get_shares():
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT * FROM ShareInfo"
            cursor.execute(query)
            result = cursor.fetchall()
            if result:
                return result
            else:
                return None
    finally:
        release_connection(connection)


def update_share_price(ticker, actual_price):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "UPDATE ShareInfo SET actualPrice = %s WHERE ticker = %s"
            values = (actual_price, ticker)
            cursor.execute(query, values)
        connection.commit()
    finally:
        release_connection(connection)


def get_share_by_ticker(ticker):
    connection = get_connection()
    try:
        with connection.cursor(buffered=True) as cursor:
            query = "SELECT * FROM ShareInfo WHERE ticker = %s"
            cursor.execute(query, (ticker,))
            result = cursor.fetchone()
            if result:
                return result
            else:
                return None
    finally:
        release_connection(connection)


def get_share_by_id(share_id):
    connection = get_connection()
    try:
        with connection.cursor(buffered=True) as cursor:
            query = "SELECT * FROM ShareInfo WHERE id = %s"
            cursor.execute(query, (share_id,))
            result = cursor.fetchone()
            if result:
                return result
            else:
                return None
    finally:
        release_connection(connection)


def get_last_stock_price(share_id):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT close FROM StockPrices WHERE share_id = %s ORDER BY date DESC LIMIT 1"
            cursor.execute(query, (share_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
    finally:
        release_connection(connection)


def insert_stock_price(share_id, date, open_price, high_price, low_price, close_price, volume):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO stockprices (share_id, date, open, high, low, close, volume) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            values = (share_id, date, open_price, high_price, low_price, close_price, volume)
            cursor.execute(query, values)
        connection.commit()
    finally:
        release_connection(connection)


def get_users_shares(user_id):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT * FROM usershares WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
    finally:
        release_connection(connection)


def get_user_shares_by_period(user_id, start_date, end_date):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # Формирование SQL-запроса для получения акций пользователя за заданный период
            query = "SELECT * FROM usershares WHERE user_id = %s AND purchase_date BETWEEN %s AND %s"
            values = (user_id, start_date, end_date)

            # Выполнение SQL-запроса
            cursor.execute(query, values)

            # Получение результатов запроса
            user_shares = []
            for row in cursor.fetchall():
                share = {
                    'id': row[0],
                    'user_id': row[1],
                    'share_id': row[2],
                    'quantity': row[3],
                    'purchase_price': row[4],
                    'purchase_date': row[5]
                }
                user_shares.append(share)

            return user_shares
    finally:
        release_connection(connection)


def insert_share_to_portfolio(user_id, share_id, quantity, purchase_price, purchase_date):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO usershares (user_id, share_id, quantity, purchase_price, purchase_date) VALUES (%s, %s, %s, %s, %s)"
            values = (user_id, share_id, quantity, purchase_price, purchase_date)
            cursor.execute(query, values)
        connection.commit()
    finally:
        release_connection(connection)


# Функция для добавления пользователя
def add_user(user):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # Вставка записи в таблицу Users
            query_users = "INSERT INTO users (name, lastname) VALUES (%s, %s)"
            values_users = (user["name"], user["lastname"])
            cursor.execute(query_users, values_users)
            user_id = cursor.lastrowid

            # Вставка записи в таблицу UserLogin
            query_user_login = "INSERT INTO userlogin (user_id, email, password) VALUES (%s, %s, %s)"
            values_user_login = (user_id, user["email"], user["password"])
            cursor.execute(query_user_login, values_user_login)

        connection.commit()
        return user_id
    finally:
        release_connection(connection)


# Функция для обновления пользователя
def update_user(user_id, updates):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "UPDATE Users SET name = %s, email = %s, password = %s WHERE id = %s"
            values = (updates["name"], updates["email"], updates["password"], user_id)
            cursor.execute(query, values)
        connection.commit()
        return cursor.rowcount
    finally:
        release_connection(connection)


# Функция для получения информации о ценных бумагах по тикеру
def get_stock_info_by_ticker(ticker):
    connection = get_connection()
    try:
        with connection.cursor(buffered=True) as cursor:
            query = "SELECT * FROM shareinfo WHERE ticker = %s"
            cursor.execute(query, (ticker,))
            result = cursor.fetchone()
            return result
    finally:
        release_connection(connection)


# Функция для получения информации о всех ценных бумагах
def get_stock_info():
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT * FROM shareinfo"
            cursor.execute(query)
            return cursor.fetchall()
    finally:
        release_connection(connection)


# Функция для получения цен на ценные бумаги по тикеру
def get_stock_prices(share_id):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT date, open, high, low, close, volume FROM stockprices WHERE share_id = %s"
            cursor.execute(query, (share_id,))
            return cursor.fetchall()
    finally:
        release_connection(connection)
