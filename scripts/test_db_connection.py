import psycopg2

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "test123",
    "database": "vectordb"
}

try:
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # 查詢 pgvector 擴展
    cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
    result = cursor.fetchone()
    
    if result:
        print("✅ pgvector 已安裝")
    else:
        print("❌ pgvector 未安裝，建立中...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        print("✅ pgvector 已建立")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 連接失敗：{e}")