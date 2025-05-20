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
    # Total Registered Youth by Barangay
    barangay_counts = db.session.query(
        KKProfile.Barangay,
        func.count(KKProfile.Respondent_No)
    ).group_by(KKProfile.Barangay).all()
    barangay_labels = [b for b, _ in barangay_counts]
    barangay_data = [c for _, c in barangay_counts]
    barangay_chart = {
        "labels": barangay_labels,
        "datasets": [{
            "label": "Total Youth",
            "data": barangay_data,
            "backgroundColor": "rgba(54, 162, 235, 0.6)"
        }]
    }

    # Age Group Distribution
    age_groups = {'15-17': 0, '18-21': 0, '22-24': 0, '25-30': 0}
    for profile in KKProfile.query.all():
        try:
            age = int(profile.Age) if profile.Age is not None else 0
            if 15 <= age <= 17:
                age_groups['15-17'] += 1
            elif 18 <= age <= 21:
                age_groups['18-21'] += 1
            elif 22 <= age <= 24:
                age_groups['22-24'] += 1
            elif 25 <= age <= 30:
                age_groups['25-30'] += 1
        except Exception:
            continue
    age_group_chart = {
        "labels": list(age_groups.keys()),
        "datasets": [{
            "data": list(age_groups.values()),
            "backgroundColor": [
                "rgba(255, 99, 132, 0.5)",
                "rgba(54, 162, 235, 0.5)",
                "rgba(255, 206, 86, 0.5)",
                "rgba(75, 192, 192, 0.5)"
            ]
        }]
    }

    # Gender Distribution
    gender_counts = db.session.query(
        KKProfile.Sex_Assigned_by_Birth,
        func.count(KKProfile.Respondent_No)
    ).group_by(KKProfile.Sex_Assigned_by_Birth).all()
    gender_labels = [g for g, _ in gender_counts]
    gender_data = [c for _, c in gender_counts]
    gender_chart = {
        "labels": gender_labels,
        "datasets": [{
            "data": gender_data,
            "backgroundColor": [
                "rgba(54, 162, 235, 0.5)",
                "rgba(255, 99, 132, 0.5)"
            ]
        }]
    }

    # Educational Attainment Breakdown
    education_counts = db.session.query(
        KKDemographics.Educational_Background,
        func.count(KKDemographics.Respondent_No)
    ).group_by(KKDemographics.Educational_Background).all()
    education_labels = [e for e, _ in education_counts]
    education_data = [c for _, c in education_counts]
    education_chart = {
        "labels": education_labels,
        "datasets": [{
            "label": "Number of Youth",
            "data": education_data,
            "backgroundColor": "rgba(75, 192, 192, 0.5)"
        }]
    }

    # Youth Employment Status Summary
    employment_counts = db.session.query(
        KKDemographics.Work_Status,
        func.count(KKDemographics.Respondent_No)
    ).group_by(KKDemographics.Work_Status).all()
    employment_labels = [e for e, _ in employment_counts]
    employment_data = [c for _, c in employment_counts]
    employment_chart = {
        "labels": employment_labels,
        "datasets": [{
            "data": employment_data,
            "backgroundColor": [
                "rgba(255, 99, 132, 0.5)",
                "rgba(54, 162, 235, 0.5)",
                "rgba(255, 206, 86, 0.5)"
            ]
        }]
    }

    # Barangay-wise Youth Engagement Level (example: use same as barangay for now)
    engagement_chart = {
        "labels": barangay_labels,
        "datasets": [{
            "label": "Engagement",
            "data": barangay_data,
            "backgroundColor": "rgba(75, 192, 192, 0.5)"
        }]
    }

    # Support Needs Level (example: dummy data)
    support_needs_chart = {
        "labels": ["High", "Medium", "Low"],
        "datasets": [{
            "data": [10, 20, 30],
            "backgroundColor": [
                "rgba(255, 99, 132, 0.5)",
                "rgba(255, 206, 86, 0.5)",
                "rgba(75, 192, 192, 0.5)"
            ]
        }]
    }

    # Program Attendance Trends (dummy data, replace with real query)
    attendance_chart = {
        "labels": ["Jan", "Feb", "Mar", "Apr"],
        "datasets": [{
            "label": "Attendance",
            "data": [100, 120, 90, 110],
            "backgroundColor": "rgba(153, 102, 255, 0.5)",
            "borderColor": "rgba(153, 102, 255, 1)",
            "fill": False,
            "tension": 0.1
        }]
    }

    dashboard_data = {
        "barangayData": barangay_chart,
        "ageGroupData": age_group_chart,
        "genderData": gender_chart,
        "educationData": education_chart,
        "attendanceData": attendance_chart,
        "employmentData": employment_chart,
        "engagementData": engagement_chart,
        "supportNeedsData": support_needs_chart,
    }

    # Example summary values
    total_youth = sum(barangay_data)
    active_programs = 3
    avg_engagement = 50.9
    total_barangays = len(barangay_labels)

    return render_template(
        'dashboard.html',
        dashboard_data=dashboard_data,
        total_youth=total_youth,
        active_programs=active_programs,
        avg_engagement=avg_engagement,
        total_barangays=total_barangays
    )


