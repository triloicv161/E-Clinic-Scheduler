import mysql.connector

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",             # thay bằng user MySQL của bạn
            password="DNoHz137@",# thay bằng password của bạn
            database="clinic_scheduler",
            auth_plugin='mysql_native_password'
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối MySQL: {err}")
        return None
