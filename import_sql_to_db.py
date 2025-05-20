import os
from sqlalchemy import create_engine, text

# Path to your SQLite DB (adjust if needed)
db_path = os.path.join('instance', 'youth_governance.db')
db_uri = f'sqlite:///{db_path}'

# Path to your SQL file
sql_file = 'kk_db.sql'

def clean_sql(sql):
    lines = []
    for line in sql.splitlines():
        l = line.strip()
        # Skip MySQL-specific lines and comments
        if (
            l.startswith('--') or
            l.startswith('/*!') or
            l.startswith('LOCK TABLES') or
            l.startswith('UNLOCK TABLES') or
            l.startswith('COMMIT') or
            'ENGINE=' in l or
            'AUTO_INCREMENT' in l or
            'UNIQUE KEY' in l or
            'KEY ' in l or
            l.startswith('ALTER TABLE') and ('ADD KEY' in l or 'ADD CONSTRAINT' in l)
        ):
            continue
        # Remove MySQL backticks
        line = line.replace('`', '')
        # Replace MySQL int(11) with SQLite int
        line = line.replace('int(11)', 'INTEGER')
        # Replace MySQL varchar with SQLite TEXT
        line = line.replace('varchar(', 'TEXT(')
        lines.append(line)
    return '\n'.join(lines)

def import_sql():
    # Create the database file if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
    engine = create_engine(db_uri)

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_statements = clean_sql(f.read())

    with engine.connect() as conn:
        for statement in sql_statements.split(';'):
            stmt = statement.strip()
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    print(f"Error executing statement: {stmt[:100]}... \n{e}")

    print(f"Data imported to {db_path}")

if __name__ == '__main__':
    import_sql()