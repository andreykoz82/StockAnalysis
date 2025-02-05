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

# Список актуальной номенклатуры
item_list = 'Бронхофитол® плющ сироп 100 мл'


train_end = '2025-01-31'
forecast_start = '2025-02-01'
forecast_end = '2025-02-28'
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


sales_by_item_sql = f"""
SELECT "Дата", "Продажи"
FROM public.sales
WHERE "Номенклатура" = '{item_list}'
"""

sales_by_item = pd.read_sql_query(sales_by_item_sql, engine).set_index('Дата')

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
timesfm_forecast['item'] = item_list
sales_forecast = pd.concat([timesfm_forecast, sales_forecast], axis=0)
