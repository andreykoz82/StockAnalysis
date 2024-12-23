# %%
import warnings
import pandas as pd
from sqlalchemy import create_engine
import timesfm
import numpy as np

warnings.filterwarnings('ignore')

# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# Список актуальной номенклатуры
actual_items = pd.read_sql_query(
    """
    SELECT "Наименование"
    FROM public.actual_items
    """,
    con=engine
)
item_list = actual_items['Наименование'].sort_values().to_list()

train_end = '2024-11-30'
forecast_start = '2024-12-01'
forecast_end = '2025-01-31'

forecast_results = []

sales_forecast = pd.DataFrame([{'ds':None, 'timesfm':None, 'item':None}])

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

    train = sales_by_item[sales_by_item.index < train_end].resample('M').sum()
    prediction_length = (pd.Timestamp(forecast_end) - pd.Timestamp(forecast_start)).days

    # Модель Google TimesFM
    df = pd.DataFrame({'unique_id': [1] * len(train),
                       'ds': train.index,
                       "y": train['Продажи']})
    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend="cpu",
            per_core_batch_size=32,
            horizon_len=prediction_length,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(
            huggingface_repo_id="google/timesfm-1.0-200m-pytorch"),
    )
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
sales_forecast.to_sql('sales_forecast', con=engine, if_exists='replace', index=False)