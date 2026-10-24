import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
USER, PWD = os.environ["MYSQL_USER"], os.environ["MYSQL_PWD"]
HOST, DB = os.environ["MYSQL_HOST"], os.environ["MYSQL_DB"]
engine = create_engine(f"mysql+pymysql://{USER}:{PWD}@{HOST}/{DB}")

# Dimensions are already clean: load them straight into the final tables
dims = ["dim_payer", "dim_provider", "dim_procedure", "dim_denial_code", "dim_date"]
with engine.begin() as conn:
    for t in dims:
        conn.execute(text(f"DELETE FROM {t}"))
for t in dims:
    pd.read_csv(f"data/raw/{t}.csv").to_sql(t, engine, if_exists="append", index=False)

# Claims go in untouched as text: this is the raw staging layer
claims = pd.read_csv("data/raw/claims.csv", dtype=str)
claims.to_sql("stg_claims", engine, if_exists="replace", index=False)

with engine.connect() as conn:
    print("stg_claims rows:", conn.execute(text("SELECT COUNT(*) FROM stg_claims")).scalar())