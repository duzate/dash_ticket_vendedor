import sys
sys.path.append("/home/sup/dash_ticket_vendedor")
import etl.load_dw as load_dw
import etl.sql_ddl as sql_ddl

print("Testando conexao DW (PostgreSQL)...")
engine = load_dw.connect_postgres_dw()
if engine:
    print("Conexao BEM-SUCEDIDA com PostgreSQL via SQLAlchemy!")
    
    print("Aplicando esquemas DDL no banco...")
    sql_ddl.prepare_dw(engine)
    print("Sucesso! O Schema Postgres Analítico está pronto.")
else:
    print("Falhou verifique Docker")
