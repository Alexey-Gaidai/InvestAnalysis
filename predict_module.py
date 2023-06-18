import pandas as pd
from matplotlib import pyplot as plt
from prophet import Prophet
import datetime
import database_interaction as database


def make_forecast(stock_list):
    # Создание DataFrame из списка объектов коллекции "stock"
    df = pd.DataFrame(stock_list)
    print(df)
    # Преобразование даты из числового формата в формат datetime
    if 'date' in df:
        df['date'] = pd.to_datetime(df['date'], unit='ms')

        # Переименование столбцов
    df.rename(columns={0: 'date', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)

    # Создание DataFrame с необходимыми столбцами для прогнозирования
    df_prophet = df[['date', 'close']]
    df_prophet.columns = ['ds', 'y']

    best_hyperparameters = {
        "changepoint_prior_scale": 10,
        "growth": "linear",
        "holidays_prior_scale": 0.1,
        "seasonality_prior_scale": 0.1, }
    # Создание и обучение модели Prophet
    model = Prophet(**best_hyperparameters)
    model.fit(df_prophet)

    # Генерация будущих дат для прогноза
    future = model.make_future_dataframe(periods=30)

    # Предсказание цен
    forecast = model.predict(future)

    # Возврат списка прогнозов на 30 дней
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].values.tolist()


def calculate_dietz_return(user_id, start_date, end_date):
    # Получение записей из таблицы usershares для заданного пользователя и периода
    shares = database.get_user_shares_by_period(user_id, start_date, end_date)

    # Расчет начальной стоимости портфеля (VS)
    start_value = sum(share['quantity'] * share['purchase_price'] for share in shares)

    # Расчет конечной стоимости портфеля (VE)
    end_value = 0
    for share in shares:
        ticker = share['share_id']
        current_price = database.get_last_stock_price(ticker)
        if current_price:
            end_value += share['quantity'] * current_price
        else:
            # Если текущая цена недоступна, используйте последнюю известную цену акции
            last_known_price = share['last_known_price']
            end_value += share['quantity'] * last_known_price

    # Расчет доходности по Модифицированному методу Дитца (r)
    percentage_return = ((end_value - start_value) / start_value) * 100
    monetary_return = end_value - start_value

    return round(percentage_return, 2), monetary_return
