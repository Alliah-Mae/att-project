# app/models.py

from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class KKProfile(db.Model):
    __tablename__ = 'kk_profile'
    Respondent_No = db.Column(db.String(14), primary_key=True)
    Date = db.Column(db.Date)
    Last_Name = db.Column(db.String(100))
    Middle_Name = db.Column(db.String(100))
    First_Name = db.Column(db.String(100))
    Suffix = db.Column(db.String(50))
    Region = db.Column(db.String(100))
    Province = db.Column(db.String(100))
    Municipality = db.Column(db.String(100))
    Barangay = db.Column(db.String(100))
    Sex_Assigned_by_Birth = db.Column(db.String(10))
    Age = db.Column(db.Integer)
    Birthday = db.Column(db.Date)
    Email_Address = db.Column(db.String(255))
    Contact_No = db.Column(db.String(20))

    demographics = db.relationship('KKDemographics', backref='profile', uselist=False)

    def __repr__(self):
        return f"<KKProfile {self.First_Name} {self.Last_Name}>"

class KKDemographics(db.Model):
    __tablename__ = 'kk_demographics'
    Respondent_No = db.Column(db.String(14), db.ForeignKey('kk_profile.Respondent_No'), primary_key=True)
    Civil_Status = db.Column(db.String(20))
    Youth_Classification = db.Column(db.String(50))
    Youth_Age_Group = db.Column(db.String(30))
    Work_Status = db.Column(db.String(50))
    Educational_Background = db.Column(db.String(50))
    Registered_SK_Voter = db.Column(db.String(5))
    Registered_National_Voter = db.Column(db.String(5))
    Attended_KK_Assembly = db.Column(db.String(5))
    Did_you_vote_last_SK_election = db.Column(db.String(5))
    If_yeshow_many_times = db.Column(db.String(30))
    If_No_Why = db.Column(db.String(100))

    def __repr__(self):
        return f"<KKDemographics for {self.Respondent_No}>"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
