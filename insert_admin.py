from sqlalchemy import create_engine, text
import os

# Database configuration
db_path = 'instance/youth_governance.db'
db_uri = f'sqlite:///{db_path}'

def insert_admin():
    # Create engine
    engine = create_engine(db_uri)
    
    # SQL statements
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS `admin_users` (
        `admin_id` INTEGER PRIMARY KEY,
        `username` VARCHAR(100) NOT NULL,
        `password` TEXT NOT NULL
    )
    """
    
    insert_admin_sql = """
    INSERT INTO `admin_users` (`admin_id`, `username`, `password`) 
    VALUES (0, 'admin', 'admin123')
    """
    
    with engine.connect() as conn:
        # Create table if it doesn't exist
        conn.execute(text(create_table_sql))
        conn.commit()
        
        # Insert admin user
        try:
            conn.execute(text(insert_admin_sql))
            conn.commit()
            print("Admin user inserted successfully!")
        except Exception as e:
            print(f"Error inserting admin user: {e}")

if __name__ == '__main__':
    insert_admin() 