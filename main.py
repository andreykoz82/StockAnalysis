# %%
import warnings
import pandas as pd
from sqlalchemy import create_engine
import timesfm
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
current_stocks['По дням'] = pd.to_datetime(current_stocks['По дням'], dayfirst=True)
current_stocks.to_sql('current_stocks', con=engine, if_exists='replace', index=False)

# Обновление текущих продаж
sales = pd.read_excel('data/sales.xlsx')
sales['Дата'] = pd.to_datetime(sales['Дата'])
sales.to_sql('sales', con=engine, if_exists='replace', index=False)

# Обновление текущей номенклатуры
actual_items = pd.read_excel('data/actual_items.xlsx')
actual_items.to_sql('actual_items', con=engine, if_exists='replace', index=False)

# Список актуальной номенклатуры
actual_items = pd.read_sql_query(
    """
    SELECT "Наименование"
    FROM public.actual_items
    """,
    con=engine
)
item_list = actual_items['Наименование'].sort_values().to_list()

train_end = '2024-12-31'
forecast_start = '2025-01-01'
forecast_end = '2025-01-31'
# prediction_length = (pd.to_datetime(forecast_end) - pd.to_datetime(forecast_start)).days
prediction_length = 1


forecast_results = []

sales_forecast = pd.DataFrame([{'ds':None, 'timesfm':None, 'item':None}])

tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend="cpu",
            per_core_batch_size=32,
            horizon_len=prediction_length,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(
            huggingface_repo_id="google/timesfm-1.0-200m-pytorch"),
    )

for item in item_list:
    # Выгрузка данных по номенклатуре
    sales_by_item_sql = f"""
    SELECT "Дата", "Продажи"
    FROM public.sales
    WHERE "Номенклатура" = '{item}'
    """
    sales_by_item = pd.read_sql_query(sales_by_item_sql, engine).set_index('Дата')

    if sales_by_item.empty:
        continue

    train = sales_by_item[sales_by_item.index <= train_end].resample('M').sum()

    df = pd.DataFrame({'unique_id': [1] * len(train),
                       'ds': train.index,
                       "y": train['Продажи']})

    timesfm_forecast = tfm.forecast_on_df(
        inputs=df,
        freq="M",
        value_name="y",
        num_jobs=-1,
    )
    timesfm_forecast = timesfm_forecast[["ds","timesfm"]]
    timesfm_forecast['item'] = item
    sales_forecast = pd.concat([timesfm_forecast, sales_forecast], axis=0)

engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')
sales_forecast.to_sql('sales_forecast', con=engine, if_exists='append', index=False)