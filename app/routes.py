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
    
    # Get age distribution using SQL aggregation
    age_distribution = db.session.query(
        case(
            (db.and_(KKProfile.Age >= 15, KKProfile.Age <= 17), '15-17'),
            (db.and_(KKProfile.Age >= 18, KKProfile.Age <= 21), '18-21'),
            (db.and_(KKProfile.Age >= 22, KKProfile.Age <= 24), '22-24'),
            (db.and_(KKProfile.Age >= 25, KKProfile.Age <= 30), '25-30')
        ).label('age_group'),
        func.count(KKProfile.Respondent_No)
    ).group_by('age_group').all()
    
    for age_group, count in age_distribution:
        if age_group:  # Skip None values
            age_groups[age_group] = count
    
    dashboard_data['ageGroupData']['labels'] = list(age_groups.keys())
    dashboard_data['ageGroupData']['datasets'][0]['data'] = list(age_groups.values())
    
    # Get gender distribution
    gender_counts = db.session.query(
        KKProfile.Sex_Assigned_by_Birth,
        func.count(KKProfile.Respondent_No)
    ).group_by(KKProfile.Sex_Assigned_by_Birth).all()
    
    gender_data = []
    for gender, count in gender_counts:
        if gender:  # Skip None values
            gender_data.append(count)
    
    # Ensure we have data for both genders
    if len(gender_data) < 2:
        gender_data.extend([0] * (2 - len(gender_data)))
    
    dashboard_data['genderData']['datasets'][0]['data'] = gender_data
    
    # Get education distribution
    education_counts = db.session.query(
        KKDemographics.Educational_Background,
        func.count(KKDemographics.Respondent_No)
    ).group_by(KKDemographics.Educational_Background).all()
    
    education_labels = []
    education_data = []
    for education, count in education_counts:
        if education:  # Skip None values
            education_labels.append(education)
            education_data.append(count)
    
    dashboard_data['educationData']['labels'] = education_labels
    dashboard_data['educationData']['datasets'][0]['data'] = education_data
    
    # Get employment status
    employment_counts = db.session.query(
        KKDemographics.Work_Status,
        func.count(KKDemographics.Respondent_No)
    ).group_by(KKDemographics.Work_Status).all()
    
    employment_labels = []
    employment_data = []
    for status, count in employment_counts:
        if status:  # Skip None values
            employment_labels.append(status)
            employment_data.append(count)
    
    dashboard_data['employmentData']['labels'] = employment_labels
    dashboard_data['employmentData']['datasets'][0]['data'] = employment_data
    
    # Calculate engagement levels using SQL
    engagement_levels = db.session.query(
        case(
            (db.and_(
                KKDemographics.Attended_KK_Assembly == 'Yes',
                KKDemographics.Did_you_vote_last_SK_election == 'Yes'
            ), 'Highly Active'),
            (db.or_(
                KKDemographics.Attended_KK_Assembly == 'Yes',
                KKDemographics.Did_you_vote_last_SK_election == 'Yes'
            ), 'Active'),
            else_='Inactive'
        ).label('engagement_level'),
        func.count(KKProfile.Respondent_No)
    ).join(KKDemographics).group_by('engagement_level').all()
    
    engagement_data = [0, 0, 0]  # [Highly Active, Active, Inactive]
    for level, count in engagement_levels:
        if level == 'Highly Active':
            engagement_data[0] = count
        elif level == 'Active':
            engagement_data[1] = count
        else:
            engagement_data[2] = count
    
    dashboard_data['engagementData']['datasets'][0]['data'] = engagement_data
    
    # Calculate support needs using SQL
    support_needs = db.session.query(
        case(
            (db.and_(
                KKDemographics.Work_Status == 'Unemployed',
                KKDemographics.Educational_Background.in_(['Elementary', 'High School'])
            ), 'High'),
            (db.or_(
                KKDemographics.Work_Status == 'Part-time',
                KKDemographics.Educational_Background == 'College'
            ), 'Medium'),
            else_='Low'
        ).label('support_level'),
        func.count(KKProfile.Respondent_No)
    ).join(KKDemographics).group_by('support_level').all()
    
    support_data = [0, 0, 0]  # [High, Medium, Low]
    for level, count in support_needs:
        if level == 'High':
            support_data[0] = count
        elif level == 'Medium':
            support_data[1] = count
        else:
            support_data[2] = count
    
    dashboard_data['supportNeedsData']['datasets'][0]['data'] = support_data

    return render_template('dashboard.html',
                         total_youth=total_youth,
                         total_barangays=total_barangays,
                         avg_engagement=round(avg_engagement, 1),
                         active_programs=3,  # This would need to be calculated based on actual program data
                         dashboard_data=json.dumps(dashboard_data))


