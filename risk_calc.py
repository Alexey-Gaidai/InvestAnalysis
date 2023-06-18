from alpha_vantage.fundamentaldata import FundamentalData

# Задайте ваш ключ API Alpha Vantage
api_key = 'YOUR_API_KEY'

# Создайте экземпляр класса FundamentalData с использованием вашего ключа API
fd = FundamentalData(key=api_key)

# Задайте символ акции компании
symbol = 'AAPL'  # Пример для акции Apple

# Получение финансового отчета за год
data, meta_data = fd.get_income_statement_annual(symbol=symbol)

# Вывод полученных данных
print(data)
