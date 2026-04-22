from etl.load_dw import connect_postgres_dw
from sqlalchemy import text
engine = connect_postgres_dw()
with engine.begin() as conn:
    try:
        conn.execute(text("ALTER TABLE fato_vendasdiarias ADD CONSTRAINT unique_tempo_vendedor UNIQUE (id_tempo, id_vendedor);"))
        print("Constraint added successfully")
    except Exception as e:
        print("Constraint already exists or error:", e)
