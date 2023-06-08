import pandas as pd
from matplotlib import pyplot as plt
from prophet import Prophet


def make_forecast(stock_list):
    # Создание DataFrame из списка объектов коллекции "stock"
    df = pd.DataFrame(stock_list)

    # Преобразование даты из числового формата в формат datetime
    if 'date' in df:
        df['date'] = pd.to_datetime(df['date'], unit='ms')

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
