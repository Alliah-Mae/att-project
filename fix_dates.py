from sqlalchemy import create_engine, text
from datetime import datetime
import os

# Database configuration
db_path = 'instance/youth_governance.db'
db_uri = f'sqlite:///{db_path}'

def fix_dates():
    # Create engine
    engine = create_engine(db_uri)
    
    with engine.connect() as conn:
        # Get all records with dates
        result = conn.execute(text("SELECT Respondent_No, Date, Birthday FROM kk_profile"))
        records = result.fetchall()
        
        for record in records:
            respondent_no = record[0]
            date_str = record[1]
            birthday_str = record[2]
            
            # Convert Date
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    new_date = date_obj.strftime('%Y-%m-%d')
                    conn.execute(
                        text("UPDATE kk_profile SET Date = :new_date WHERE Respondent_No = :respondent_no"),
                        {"new_date": new_date, "respondent_no": respondent_no}
                    )
                except ValueError:
                    print(f"Could not convert date: {date_str}")
            
            # Convert Birthday
            if birthday_str:
                try:
                    birthday_obj = datetime.strptime(birthday_str, '%d/%m/%Y')
                    new_birthday = birthday_obj.strftime('%Y-%m-%d')
                    conn.execute(
                        text("UPDATE kk_profile SET Birthday = :new_birthday WHERE Respondent_No = :respondent_no"),
                        {"new_birthday": new_birthday, "respondent_no": respondent_no}
                    )
                except ValueError:
                    print(f"Could not convert birthday: {birthday_str}")
        
        conn.commit()
        print("Date formats have been updated successfully!")

if __name__ == '__main__':
    fix_dates() 