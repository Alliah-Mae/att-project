from sqlalchemy import create_engine, text
import os

# Database configuration
db_path = 'instance/youth_governance.db'
db_uri = f'sqlite:///{db_path}'

def create_tables():
    # Create engine
    engine = create_engine(db_uri)
    
    # SQL statement for user table only
    create_user_table_sql = """
    CREATE TABLE IF NOT EXISTS `user` (
        `id` INTEGER PRIMARY KEY AUTOINCREMENT,
        `username` VARCHAR(100) NOT NULL UNIQUE,
        `password_hash` TEXT NOT NULL
    )
    """
    
    with engine.connect() as conn:
        # Create user table
        conn.execute(text(create_user_table_sql))
        conn.commit()
        print("User table created successfully!")

if __name__ == '__main__':
    create_tables() 