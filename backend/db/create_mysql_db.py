import pymysql

# 連接到 MySQL
connection = pymysql.connect(
    host='localhost',
    user='root',
    password='database',
    charset='utf8mb4'
)

cursor = connection.cursor()

try:
    # 創建資料庫
    cursor.execute("CREATE DATABASE IF NOT EXISTS dbProject CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    connection.commit()
finally:
    cursor.close()
    connection.close()
