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
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder

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
    # Get unique barangays for the filter
    barangays = [row[0] for row in db.session.query(distinct(KKProfile.Barangay)).order_by(KKProfile.Barangay).all() if row[0]]
    return render_template('index.html', profiles=profiles, search=search, barangays=barangays)

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

@main.route('/clustering_model')
@login_required
def clustering_model():
    # 1. Fetch data from the database
    profiles = db.session.query(
        KKProfile.Respondent_No,
        KKProfile.Age,
        KKDemographics.Educational_Background,
        KKDemographics.Work_Status,
        KKDemographics.Attended_KK_Assembly,
        KKDemographics.Did_you_vote_last_SK_election,
        KKProfile.Sex_Assigned_by_Birth,
        KKProfile.Barangay
    ).join(KKDemographics, KKProfile.Respondent_No == KKDemographics.Respondent_No).all()

    # 2. Preprocess data for clustering
    data = []
    for p in profiles:
        try:
            age = int(p.Age) if p.Age is not None and str(p.Age).isdigit() else 0
        except Exception:
            age = 0
        education = p.Educational_Background or 'Unknown'
        work_status = p.Work_Status or 'Unknown'
        attended = 1 if p.Attended_KK_Assembly == 'Yes' else 0
        voted = 1 if p.Did_you_vote_last_SK_election == 'Yes' else 0
        sex = p.Sex_Assigned_by_Birth or 'Unknown'
        barangay = p.Barangay or 'Unknown'
        data.append([age, education, work_status, attended, voted, sex, barangay])

    # Encode categorical features
    education_le = LabelEncoder()
    work_le = LabelEncoder()
    educations = [row[1] for row in data]
    works = [row[2] for row in data]
    education_encoded = education_le.fit_transform(educations)
    work_encoded = work_le.fit_transform(works)

    X = np.array([
        [row[0], education_encoded[i], work_encoded[i], row[3], row[4]]
        for i, row in enumerate(data)
    ])

    # 3. Run KMeans clustering for event recommendation
    kmeans = KMeans(n_clusters=3, random_state=0).fit(X)
    labels = kmeans.labels_

    # 4. Prepare cluster summaries and chart data for the template
    event_clusters = []
    for i in range(3):
        indices = np.where(labels == i)[0]
        cluster_profiles = [profiles[j] for j in indices]
        count = len(cluster_profiles)
        # Calculate average age
        ages = [int(p.Age) for p in cluster_profiles if p.Age is not None and str(p.Age).isdigit()]
        avg_age = np.mean(ages) if ages else 0
        # Top demographic (most common sex + age group)
        from collections import Counter
        sex_counter = Counter([p.Sex_Assigned_by_Birth for p in cluster_profiles if p.Sex_Assigned_by_Birth])
        top_sex = sex_counter.most_common(1)[0][0] if sex_counter else '-'
        age_groups = [(int(p.Age) // 5 * 5) if p.Age and str(p.Age).isdigit() else None for p in cluster_profiles]
        age_group_counter = Counter([ag for ag in age_groups if ag is not None])
        top_age_group = age_group_counter.most_common(1)[0][0] if age_group_counter else '-'
        top_demo = f"{top_age_group}-{top_age_group+4}, {top_sex}" if top_age_group != '-' else '-'
        # Top engagement (most common attended/voted)
        engagement_counter = Counter([(p.Attended_KK_Assembly, p.Did_you_vote_last_SK_election) for p in cluster_profiles])
        top_engagement = engagement_counter.most_common(1)[0][0] if engagement_counter else ('-', '-')
        top_engagement_str = f"Attended: {top_engagement[0]}, Voted: {top_engagement[1]}"
        # Recommended event (dummy logic: based on top education)
        education_counter = Counter([p.Educational_Background for p in cluster_profiles if p.Educational_Background])
        top_education = education_counter.most_common(1)[0][0] if education_counter else '-'
        if top_education == 'College':
            recommended_event = 'Job Fair'
        elif top_education == 'High School':
            recommended_event = 'Leadership Camp'
        else:
            recommended_event = 'Sports Fest'
        event_clusters.append({
            "label": f"Cluster {i+1}",
            "count": int(count),
            "top_demo": top_demo,
            "top_engagement": top_engagement_str,
            "recommended_event": recommended_event
        })

    event_cluster_chart_data = {
        "datasets": [
            {
                "label": f"Cluster {i+1}",
                "data": [{"x": float(X[j][0]), "y": float(X[j][1])} for j in np.where(labels == i)[0]],
                "backgroundColor": color
            }
            for i, color in enumerate(["rgba(54, 162, 235, 0.7)", "rgba(255, 99, 132, 0.7)", "rgba(255, 206, 86, 0.7)"])
        ]
    }

    # --- Youth Needs Support ---
    # Let's cluster by participation (attended+voted), education, and employment
    participation = [row[3] + row[4] for row in data]  # attended + voted
    education_encoded2 = education_le.transform([row[1] for row in data])
    work_encoded2 = work_le.transform([row[2] for row in data])
    X2 = np.array([
        [participation[i], education_encoded2[i], work_encoded2[i]]
        for i in range(len(data))
    ])
    kmeans2 = KMeans(n_clusters=3, random_state=1).fit(X2)
    labels2 = kmeans2.labels_
    support_labels = ['High Need Group', 'Medium Need Group', 'Low Need Group']
    needs_support_groups = []
    for i in range(3):
        indices = np.where(labels2 == i)[0]
        cluster_profiles = [profiles[j] for j in indices]
        count = len(cluster_profiles)
        avg_participation = np.mean([participation[j] for j in indices]) if count else 0
        education_counter = Counter([p.Educational_Background for p in cluster_profiles if p.Educational_Background])
        common_education = education_counter.most_common(1)[0][0] if education_counter else '-'
        work_counter = Counter([p.Work_Status for p in cluster_profiles if p.Work_Status])
        common_employment = work_counter.most_common(1)[0][0] if work_counter else '-'
        # Add a simple support need level based on participation (lower participation = higher need)
        if avg_participation < 1.5:
            support_level = 'High Need'
        elif avg_participation < 2.5:
            support_level = 'Medium Need'
        else:
            support_level = 'Low Need'
        needs_support_groups.append({
            "label": support_labels[i],
            "count": int(count),
            "avg_participation": float(round(avg_participation, 2)),
            "common_education": common_education,
            "common_employment": common_employment
        })
    bar_labels = [group["label"] for group in needs_support_groups]
    bar_data = [group["count"] for group in needs_support_groups]
    needs_support_chart_data = {
        "datasets": [
            {
                "label": support_labels[i],
                "data": [
                    {"x": float(X2[j][0]), "y": float(X2[j][1])}
                    for j in np.where(labels2 == i)[0]
                ],
                "backgroundColor": color
            }
            for i, color in enumerate([
                "rgba(255, 99, 132, 0.7)",
                "rgba(255, 206, 86, 0.7)",
                "rgba(75, 192, 192, 0.7)"
            ])
        ]
    }

    return render_template(
        'clustering_model.html',
        event_clusters=event_clusters,
        event_cluster_chart_data=event_cluster_chart_data,
        needs_support_groups=needs_support_groups,
        needs_support_chart_data=needs_support_chart_data
    )


