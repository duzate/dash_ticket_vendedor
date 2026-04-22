import os
import oracledb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

user = os.environ.get("ERP_USER")
pwd = os.environ.get("ERP_PASSWORD")
dsn = os.environ.get("ERP_DSN")

print(f"Tentando conectar ao ERP em {dsn} com usuario {user}...")

try:
    conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
    print("Conexao BEM-SUCEDIDA!")
    
    # Check what tables are available matching TGF%
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM all_tables WHERE table_name LIKE 'TGF%' FETCH FIRST 20 ROWS ONLY")
    print("Tabelas encontradas (Amostra):")
    for row in cursor.fetchall():
        print(f" - {row[0]}")
        
    print("\nInspecionando Colunas de TGFCAB (Notas)....")
    cursor.execute("SELECT column_name FROM all_tab_columns WHERE table_name = 'TGFCAB' FETCH FIRST 20 ROWS ONLY")
    cols = [r[0] for r in cursor.fetchall()]
    print(", ".join(cols))
    
    print("\nInspecionando Colunas de TGFVEN (Vendedores)....")
    cursor.execute("SELECT column_name FROM all_tab_columns WHERE table_name = 'TGFVEN' FETCH FIRST 20 ROWS ONLY")
    cols = [r[0] for r in cursor.fetchall()]
    print(", ".join(cols))

    conn.close()
    
except Exception as e:
    print(f"ERRO DE CONEXAO AO ORACLE: {e}")
