# app/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import KKProfile, KKDemographics, User
from app.forms import LoginForm, RegistrationForm
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import distinct, func, case
from sqlalchemy import text
from collections import defaultdict
import json

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    query = KKProfile.query
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (KKProfile.First_Name.ilike(search_filter)) |
            (KKProfile.Last_Name.ilike(search_filter)) |
            (KKProfile.Barangay.ilike(search_filter))
        )
    profiles = query.all()
    return render_template('index.html', profiles=profiles, search=search)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main.route('/data-table')
@login_required
def data_table():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    selected_region = request.args.get('region', '')
    
    # Base query
    query = KKProfile.query
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (KKProfile.First_Name.ilike(search_filter)) |
            (KKProfile.Last_Name.ilike(search_filter)) |
            (KKProfile.Barangay.ilike(search_filter)) |
            (KKProfile.Respondent_No.ilike(search_filter))
        )
    
    # Apply region filter
    if selected_region:
        query = query.filter(KKProfile.Region == selected_region)
    
    # Get unique regions for filter dropdown
    regions = db.session.query(distinct(KKProfile.Region)).order_by(KKProfile.Region).all()
    regions = [r[0] for r in regions if r[0]]  # Remove None values
    
    # Paginate results
    per_page = 20  # Number of items per page
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    profiles = pagination.items
    
    return render_template('data_table.html',
                         profiles=profiles,
                         pagination=pagination,
                         search=search,
                         regions=regions,
                         selected_region=selected_region)

@main.route('/test-db')
def test_db():
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("SHOW TABLES;"))
            tables = [row[0] for row in result]
        return f"Tables in kk_db: {tables}"
    except Exception as e:
        return f"Database connection failed: {e}"

@main.route('/dashboard')
@login_required
def dashboard():
    # Get total youth count
    total_youth = KKProfile.query.count()
    
    # Get total barangays
    total_barangays = db.session.query(func.count(distinct(KKProfile.Barangay))).scalar()
    
    # Calculate average engagement (based on program attendance)
    avg_engagement = db.session.query(
        func.avg(case(
            (KKDemographics.Attended_KK_Assembly == 'Yes', 100),
            else_=0
        ))
    ).scalar() or 0
    
    # Prepare data for charts
    dashboard_data = {
        # Barangay distribution
        'barangayData': {
            'labels': [],
            'datasets': [{
                'label': 'Number of Youth',
                'data': [],
                'backgroundColor': 'rgba(54, 162, 235, 0.5)'
            }]
        },
        
        # Age group distribution
        'ageGroupData': {
            'labels': [],
            'datasets': [{
                'data': [],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(75, 192, 192, 0.5)'
                ]
            }]
        },
        
        # Gender distribution
        'genderData': {
            'labels': ['Male', 'Female'],
            'datasets': [{
                'data': [],
                'backgroundColor': [
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 99, 132, 0.5)'
                ]
            }]
        },
        
        # Education distribution
        'educationData': {
            'labels': [],
            'datasets': [{
                'label': 'Number of Youth',
                'data': [],
                'backgroundColor': 'rgba(75, 192, 192, 0.5)'
            }]
        },
        
        # Employment status
        'employmentData': {
            'labels': [],
            'datasets': [{
                'data': [],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 206, 86, 0.5)'
                ]
            }]
        },
        
        # Engagement levels
        'engagementData': {
            'labels': ['Highly Active', 'Active', 'Inactive'],
            'datasets': [{
                'label': 'Number of Youth',
                'data': [],
                'backgroundColor': [
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 99, 132, 0.5)'
                ]
            }]
        },
        
        # Support needs
        'supportNeedsData': {
            'labels': ['High', 'Medium', 'Low'],
            'datasets': [{
                'data': [],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(75, 192, 192, 0.5)'
                ]
            }]
        }
    }
    
    # Get barangay distribution
    barangay_counts = db.session.query(
        KKProfile.Barangay,
        func.count(KKProfile.Respondent_No)
    ).group_by(KKProfile.Barangay).all()
    
    for barangay, count in barangay_counts:
        dashboard_data['barangayData']['labels'].append(barangay)
        dashboard_data['barangayData']['datasets'][0]['data'].append(count)
    
    # Get age group distribution
    age_groups = {
        '15-17': 0,
        '18-21': 0,
        '22-24': 0,
        '25-30': 0
    }
    
    for profile in KKProfile.query.all():
        age = profile.Age
        if 15 <= age <= 17:
            age_groups['15-17'] += 1
        elif 18 <= age <= 21:
            age_groups['18-21'] += 1
        elif 22 <= age <= 24:
            age_groups['22-24'] += 1
        elif 25 <= age <= 30:
            age_groups['25-30'] += 1
    
    dashboard_data['ageGroupData']['labels'] = list(age_groups.keys())
    dashboard_data['ageGroupData']['datasets'][0]['data'] = list(age_groups.values())
    
    # Get gender distribution
    gender_counts = db.session.query(
        KKProfile.Sex_Assigned_by_Birth,
        func.count(KKProfile.Respondent_No)
    ).group_by(KKProfile.Sex_Assigned_by_Birth).all()
    
    for gender, count in gender_counts:
        if gender:
            dashboard_data['genderData']['datasets'][0]['data'].append(count)
    
    # Get education distribution
    education_counts = db.session.query(
        KKDemographics.Educational_Background,
        func.count(KKDemographics.Respondent_No)
    ).group_by(KKDemographics.Educational_Background).all()
    
    for education, count in education_counts:
        if education:
            dashboard_data['educationData']['labels'].append(education)
            dashboard_data['educationData']['datasets'][0]['data'].append(count)
    
    # Get employment status
    employment_counts = db.session.query(
        KKDemographics.Work_Status,
        func.count(KKDemographics.Respondent_No)
    ).group_by(KKDemographics.Work_Status).all()
    
    for status, count in employment_counts:
        if status:
            dashboard_data['employmentData']['labels'].append(status)
            dashboard_data['employmentData']['datasets'][0]['data'].append(count)
    
    # Calculate engagement levels
    engagement_levels = {
        'Highly Active': 0,
        'Active': 0,
        'Inactive': 0
    }
    
    for profile in KKProfile.query.join(KKDemographics).all():
        if profile.demographics:
            if profile.demographics.Attended_KK_Assembly == 'Yes' and profile.demographics.Did_you_vote_last_SK_election == 'Yes':
                engagement_levels['Highly Active'] += 1
            elif profile.demographics.Attended_KK_Assembly == 'Yes' or profile.demographics.Did_you_vote_last_SK_election == 'Yes':
                engagement_levels['Active'] += 1
            else:
                engagement_levels['Inactive'] += 1
    
    dashboard_data['engagementData']['datasets'][0]['data'] = list(engagement_levels.values())
    
    # Calculate support needs (example calculation based on employment and education)
    support_needs = {
        'High': 0,
        'Medium': 0,
        'Low': 0
    }
    
    for profile in KKProfile.query.join(KKDemographics).all():
        if profile.demographics:
            if profile.demographics.Work_Status == 'Unemployed' and profile.demographics.Educational_Background in ['Elementary', 'High School']:
                support_needs['High'] += 1
            elif profile.demographics.Work_Status == 'Part-time' or profile.demographics.Educational_Background == 'College':
                support_needs['Medium'] += 1
            else:
                support_needs['Low'] += 1
    
    dashboard_data['supportNeedsData']['datasets'][0]['data'] = list(support_needs.values())
    
    return render_template('dashboard.html',
                         total_youth=total_youth,
                         total_barangays=total_barangays,
                         avg_engagement=round(avg_engagement, 1),
                         active_programs=3,  # This would need to be calculated based on actual program data
                         dashboard_data=json.dumps(dashboard_data))


