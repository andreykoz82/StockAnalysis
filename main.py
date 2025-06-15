# %%
import warnings
import pandas as pd
from sqlalchemy import create_engine
import os


warnings.filterwarnings('ignore')
os.environ['CURL_CA_BUNDLE'] = ''

# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# Обновление текущих остатков НФП
current_stocks = pd.read_excel('data/semifinished_stocks.xlsx')
current_stocks.to_sql('semifinished_stocks', con=engine, if_exists='replace', index=False)

# Обновление текущих остатков готовой продукции
current_stocks = pd.read_excel('data/finished_goods_stocks.xlsx')
# current_stocks['По дням'] = pd.to_datetime(current_stocks['По дням'], dayfirst=True)
current_stocks.to_sql('current_stocks', con=engine, if_exists='replace', index=False)

# Обновление текущих продаж
sales = pd.read_excel('data/sales.xlsx')
sales['Дата'] = pd.to_datetime(sales['Дата'])
sales.to_sql('sales', con=engine, if_exists='replace', index=False)

# Текущие заказы
actual_orders = pd.read_excel('data/actual_orders_2stage.xlsx')
actual_orders.to_sql('actual_orders', con=engine, if_exists='replace', index=False)

# Обновление остатков печатных материалов
materials_current_stocks = pd.read_excel('data/materials_stocks.xlsx')
materials_current_stocks.to_sql('materials_stocks', con=engine, if_exists='replace', index=False)

# Обновление данных по выпуску ГП
production_2_stage = pd.read_excel('data/production_2_stage.xlsx')
production_2_stage['Период'] = pd.to_datetime(production_2_stage['Период'])
production_2_stage.to_sql('production_2_stage', con=engine, if_exists='replace', index=False)

# Обновление текущей номенклатуры
actual_items = pd.read_excel('data/actual_items.xlsx')
actual_items.to_sql('actual_items', con=engine, if_exists='replace', index=False)
