import sqlalchemy
from sqlalchemy import create_engine, inspect

DATABASE_URL = "postgresql://linkedin_owner:npg_aJcpCgkA1RN6@ep-quiet-tree-a5o8mr54-pooler.us-east-2.aws.neon.tech/linkedin?sslmode=require"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    for schema in schemas:
        print(f"schema: {schema}")
        for table_name in inspector.get_table_names(schema=schema):
            print(f"table: {table_name}")
