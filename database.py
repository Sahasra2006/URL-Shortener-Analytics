import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="url_analytics",
    user="postgres",
    password="Sahasra1230@"
)

cursor = conn.cursor()
print("Database connected successfully!")