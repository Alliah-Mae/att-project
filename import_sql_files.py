import sqlite3

def execute_sql_file(db_path, sql_file_path):
    with open(sql_file_path, 'r', encoding='utf-8') as file:
        sql_script = file.read()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.executescript(sql_script)
        print(f"Executed {sql_file_path} successfully.")
    except sqlite3.Error as e:
        print(f"Error executing {sql_file_path}: {e}")
    finally:
        conn.commit()
        conn.close()

if __name__ == '__main__':
    db_path = 'instance/youth_governance.db'  # Path to your SQLite DB
    profile_sql_path = 'profile.sql'          # Your profile.sql file path
    demo_sql_path = 'demo.sql'                # Your demo.sql file path
    

    execute_sql_file(db_path, demo_sql_path)
    execute_sql_file(db_path, profile_sql_path)
