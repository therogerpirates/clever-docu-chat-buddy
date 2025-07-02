import sqlalchemy
from sqlalchemy import create_engine, inspect

DATABASE_URL = "postgresql://linkedin_owner:npg_aJcpCgkA1RN6@ep-quiet-tree-a5o8mr54-pooler.us-east-2.aws.neon.tech/linkedin?sslmode=require"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    connection.execute(sqlalchemy.text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    print("All tables in 'public' schema dropped and schema recreated.")
