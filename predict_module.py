import pandas as pd
from prophet import Prophet

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


class Prophet_Prediction:
    def __init__(self, dataset, forecats_period):
        self.df = self.dataset_preprocessing(dataset.copy())
        self.forecats_period = forecats_period

    def dataset_preprocessing(self, dataset):
        hist = dataset
        hist.reset_index(level=0, inplace=True)
        hist = hist.rename({'date': 'ds', 'close': 'y'}, axis='columns')
        return hist

    def model_learning(self):
        from prophet import Prophet

        model = Prophet(daily_seasonality=True)
        model.fit(self.df)

        return model

    def forecast(self):
        model = self.model_learning()
        future = model.make_future_dataframe(periods=self.forecats_period)
        forecast = model.predict(future)[['ds', 'yhat']]

        forecast = forecast.rename({'ds': 'date', 'yhat': 'close'}, axis='columns')
        forecast.set_index('date', inplace=True)

        return forecast[-self.forecats_period:]


class RNN_LSTM_Prediction:
    def __init__(self, dataset, forecast_period):
        from sklearn.preprocessing import StandardScaler
        self.df = dataset.copy().filter(['close'])
        self.forecast_period = forecast_period
        self.forecast
        self.x_pred = 0
        self.scaler = StandardScaler()

    def sequential_split(self, sequence_length, data):

        import numpy as np

        x = []
        y = []

        for index in range(sequence_length, len(data)):
            x.append(data[index - sequence_length:index])
            y.append(data[index])

        x, y = np.array(x), np.array(y)

        return np.reshape(x, (x.shape[0], x.shape[1], 1)), y

    def train_test_split(self):

        import math

        SEQUENCE_LENGTH = 30

        dataset = self.df.values
        train_len = math.ceil(len(dataset) * .8)

        train_data = dataset[:train_len]
        x_train, y_train = self.sequential_split(SEQUENCE_LENGTH, self.scaler.fit_transform(train_data))

        test_data = dataset[train_len:]
        x_test, y_test = self.sequential_split(SEQUENCE_LENGTH, self.scaler.transform(test_data))

        self.x_pred = x_test[-1].reshape(1, -1)

        return x_train, y_train

    def model_learning(self):
        from keras.models import Sequential
        from keras.layers import Dense, LSTM

        x_train, y_train = self.train_test_split()

        model = Sequential()
        model.add(LSTM(50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
        model.add(LSTM(50, return_sequences=False))
        model.add(Dense(25))
        model.add(Dense(1))

        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(x_train, y_train, batch_size=64, epochs=5)

        return model

    def forecast(self):

        from datetime import datetime
        import numpy as np

        model = self.model_learning()

        forecast = []
        SEQUENCE_LENGTH = 30
        i = 0
        fut_inp = self.x_pred
        tmp_inp = list(fut_inp)
        tmp_inp = tmp_inp[0].tolist()

        while (i < self.forecast_period):

            if (len(tmp_inp) > SEQUENCE_LENGTH):
                fut_inp = np.array(tmp_inp[1:])
                fut_inp = fut_inp.reshape(1, -1)
                fut_inp = fut_inp.reshape((1, SEQUENCE_LENGTH, 1))
                yhat = model.predict(fut_inp)
                tmp_inp.extend(yhat[0].tolist())
                tmp_inp = tmp_inp[1:]
                forecast.extend(yhat.tolist())
                i = i + 1
            else:
                fut_inp = fut_inp.reshape((1, SEQUENCE_LENGTH, 1))
                yhat = model.predict(fut_inp)
                tmp_inp.extend(yhat[0].tolist())
                forecast.extend(yhat.tolist())
                i = i + 1

        forecast = self.scaler.inverse_transform(forecast)

        SECONDS_IN_DAY = 86400

        last_date = self.df.index[-1]
        last_unix = last_date.timestamp()
        next_unix = last_unix + SECONDS_IN_DAY

        self.df['forecast'] = np.nan

        for value in forecast:
            next_date = datetime.fromtimestamp(next_unix)
            next_unix += SECONDS_IN_DAY
            self.df.loc[next_date] = [np.nan for _ in range(len(self.df.columns) - 1)] + [value]

        return self.df['forecast'].tail(30)


class LinReg_Prediction:
    def __init__(self, dataset, forecats_period):
        self.df = self.dataset_preprocessing(dataset.copy())
        self.forecats_period = forecats_period
        self.X_test = 0

    def dataset_preprocessing(self, dataset):
        dataset['hl_pct'] = (dataset['high'] - dataset['low']) / dataset['low'] * 100.0
        dataset['pct_change'] = (dataset['close'] - dataset['open']) / dataset['open'] * 100.0
        return dataset[['hl_pct', 'pct_change', 'close', 'volume']]

    def train_test_split(self):
        import numpy as np
        from sklearn.preprocessing import StandardScaler

        X = np.array(self.df)
        scaler = StandardScaler()
        scaler.fit_transform(X)

        self.X_test = X[-self.forecats_period:]
        X_train = X[:-self.forecats_period]

        label = self.df['close'].shift(-self.forecats_period)
        label.dropna(inplace=True)
        y_train = np.array(label)

        return X_train, y_train

    def model_learning(self):
        from sklearn.linear_model import LinearRegression

        X_train, y_train = self.train_test_split()

        model = LinearRegression()
        model.fit(X_train, y_train)

        return model

    def forecast(self, forecats_period):
        from datetime import datetime
        import numpy as np

        SECONDS_IN_DAY = 86400

        last_date = self.df.index[-1]
        last_unix = last_date.timestamp()
        next_unix = last_unix + SECONDS_IN_DAY

        model = self.model_learning()
        forecast = model.predict(self.X_test)
        self.df['forecast'] = np.nan

        for value in forecast:
            next_date = datetime.fromtimestamp(next_unix)
            next_unix += SECONDS_IN_DAY
            self.df.loc[next_date] = [np.nan for _ in range(len(self.df.columns) - 1)] + [value]

        return self.df[['forecast']].tail(forecats_period)
