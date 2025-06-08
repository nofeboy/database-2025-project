import mysql.connector
from mysql.connector import Error

try:
    conn = mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='tpgus1260!',
        database='kobis_db'
    )
    print("✅ 연결 성공!")
    conn.close()
except Error as e:
    print(f"❌ 연결 실패: {e}")
