# app/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import KKProfile, KKDemographics, User
from app.forms import LoginForm, RegistrationForm
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import distinct, func, case
from sqlalchemy import text
from collections import defaultdict
from collections import Counter
import json
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import silhouette_score

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

def get_intelligent_recommendation(education, work_status, sex, age_group, engagement_level, avg_age):
    """
    Generate intelligent event/program recommendations based on demographics aligned with 17 SDGs
    """
    recommendations = []
    
    # SDG 1: No Poverty - Employment and Economic Empowerment
    if work_status == 'Unemployed':
        recommendations.extend([
            'SDG 1: Poverty Alleviation Workshop',
            'SDG 1: Financial Literacy Training',
            'SDG 1: Micro-entrepreneurship Program',
            'SDG 1: Job Skills Development',
            'SDG 1: Economic Empowerment Initiative'
        ])
    
    # SDG 2: Zero Hunger - Food Security and Nutrition
    if education in ['Elementary graduate', 'Elementary undergraduate'] or avg_age < 20:
        recommendations.extend([
            'SDG 2: Nutrition Education Program',
            'SDG 2: Community Garden Initiative',
            'SDG 2: Food Security Workshop',
            'SDG 2: Sustainable Agriculture Training',
            'SDG 2: Healthy Eating Campaign'
        ])
    
    # SDG 3: Good Health and Well-being - Health Programs
    if sex == 'Female' or age_group == 'Teen':
        recommendations.extend([
            'SDG 3: Mental Health Awareness',
            'SDG 3: Reproductive Health Education',
            'SDG 3: Physical Wellness Program',
            'SDG 3: Substance Abuse Prevention',
            'SDG 3: Healthcare Access Workshop'
        ])
    
    # SDG 4: Quality Education - Educational Programs
    if education in ['High school graduate', 'High school undergraduate']:
        recommendations.extend([
            'SDG 4: Digital Literacy Training',
            'SDG 4: STEM Education Program',
            'SDG 4: Life Skills Development',
            'SDG 4: Academic Excellence Support',
            'SDG 4: Vocational Skills Training'
        ])
    elif education in ['Elementary graduate', 'Elementary undergraduate']:
        recommendations.extend([
            'SDG 4: Basic Literacy Program',
            'SDG 4: Numeracy Skills Training',
            'SDG 4: Computer Basics Course',
            'SDG 4: Language Development',
            'SDG 4: Educational Support Program'
        ])
    
    # SDG 5: Gender Equality - Gender Empowerment
    if sex == 'Female':
        recommendations.extend([
            'SDG 5: Women Leadership Program',
            'SDG 5: Gender Equality Workshop',
            'SDG 5: Women in STEM Initiative',
            'SDG 5: Economic Empowerment for Women',
            'SDG 5: Women\'s Rights Advocacy'
        ])
    elif sex == 'Male':
        recommendations.extend([
            'SDG 5: Men for Gender Equality',
            'SDG 5: Positive Masculinity Workshop',
            'SDG 5: Gender Sensitivity Training',
            'SDG 5: Allyship Development Program',
            'SDG 5: Gender Equality Advocacy'
        ])
    
    # SDG 6: Clean Water and Sanitation - Environmental Health
    if engagement_level < 0.5:  # Low engagement - community building
        recommendations.extend([
            'SDG 6: Water Conservation Workshop',
            'SDG 6: Sanitation Awareness Program',
            'SDG 6: Environmental Health Training',
            'SDG 6: Community Clean-up Initiative',
            'SDG 6: Water Safety Education'
        ])
    
    # SDG 7: Affordable and Clean Energy - Energy Education
    if education in ['College graduate', 'College undergraduate']:
        recommendations.extend([
            'SDG 7: Renewable Energy Workshop',
            'SDG 7: Energy Conservation Training',
            'SDG 7: Green Technology Program',
            'SDG 7: Sustainable Energy Initiative',
            'SDG 7: Energy Efficiency Workshop'
        ])
    
    # SDG 8: Decent Work and Economic Growth - Employment
    if work_status == 'Unemployed' or age_group == 'Young Adult':
        recommendations.extend([
            'SDG 8: Career Development Program',
            'SDG 8: Entrepreneurship Training',
            'SDG 8: Professional Skills Workshop',
            'SDG 8: Job Market Preparation',
            'SDG 8: Economic Growth Initiative'
        ])
    
    # SDG 9: Industry, Innovation and Infrastructure - Innovation
    if education in ['College graduate', 'College undergraduate'] or age_group == 'Young Adult':
        recommendations.extend([
            'SDG 9: Innovation Workshop',
            'SDG 9: Technology Skills Training',
            'SDG 9: Digital Infrastructure Program',
            'SDG 9: Industry 4.0 Awareness',
            'SDG 9: Innovation Hub Initiative'
        ])
    
    # SDG 10: Reduced Inequalities - Social Inclusion
    if engagement_level < 0.5 or education in ['Elementary graduate', 'Elementary undergraduate']:
        recommendations.extend([
            'SDG 10: Social Inclusion Program',
            'SDG 10: Diversity Training Workshop',
            'SDG 10: Equal Opportunity Initiative',
            'SDG 10: Community Integration Program',
            'SDG 10: Anti-Discrimination Workshop'
        ])
    
    # SDG 11: Sustainable Cities and Communities - Urban Development
    if age_group == 'Young Adult' or age_group == 'Adult':
        recommendations.extend([
            'SDG 11: Urban Planning Workshop',
            'SDG 11: Community Development Program',
            'SDG 11: Sustainable City Initiative',
            'SDG 11: Public Space Improvement',
            'SDG 11: Urban Innovation Program'
        ])
    
    # SDG 12: Responsible Consumption and Production - Sustainability
    if engagement_level > 1.5:  # High engagement - leadership
        recommendations.extend([
            'SDG 12: Sustainable Living Workshop',
            'SDG 12: Circular Economy Training',
            'SDG 12: Waste Reduction Program',
            'SDG 12: Green Consumerism Initiative',
            'SDG 12: Sustainable Production Workshop'
        ])
    
    # SDG 13: Climate Action - Environmental Protection
    if age_group == 'Teen' or engagement_level > 1.0:
        recommendations.extend([
            'SDG 13: Climate Change Awareness',
            'SDG 13: Environmental Protection Program',
            'SDG 13: Carbon Footprint Workshop',
            'SDG 13: Climate Action Initiative',
            'SDG 13: Green Advocacy Training'
        ])
    
    # SDG 14: Life Below Water - Marine Conservation
    if engagement_level > 0.5:  # Moderate to high engagement
        recommendations.extend([
            'SDG 14: Marine Conservation Workshop',
            'SDG 14: Ocean Protection Program',
            'SDG 14: Coastal Clean-up Initiative',
            'SDG 14: Marine Life Awareness',
            'SDG 14: Ocean Sustainability Training'
        ])
    
    # SDG 15: Life on Land - Terrestrial Conservation
    if age_group == 'Teen' or age_group == 'Young Adult':
        recommendations.extend([
            'SDG 15: Biodiversity Conservation',
            'SDG 15: Forest Protection Program',
            'SDG 15: Wildlife Awareness Workshop',
            'SDG 15: Land Restoration Initiative',
            'SDG 15: Ecosystem Protection Training'
        ])
    
    # SDG 16: Peace, Justice and Strong Institutions - Governance
    if engagement_level > 1.5 or education in ['College graduate', 'College undergraduate']:
        recommendations.extend([
            'SDG 16: Good Governance Workshop',
            'SDG 16: Human Rights Education',
            'SDG 16: Peace Building Program',
            'SDG 16: Justice System Awareness',
            'SDG 16: Civic Engagement Initiative'
        ])
    
    # SDG 17: Partnerships for the Goals - Collaboration
    if engagement_level > 1.0:  # Moderate to high engagement
        recommendations.extend([
            'SDG 17: Global Partnership Workshop',
            'SDG 17: International Cooperation Program',
            'SDG 17: Cross-cultural Exchange Initiative',
            'SDG 17: Partnership Building Training',
            'SDG 17: Collaborative Development Program'
        ])
    
    # Remove duplicates and select top 3 most relevant
    unique_recommendations = list(set(recommendations))
    
    # Prioritize based on combination of factors
    priority_scores = {}
    for rec in unique_recommendations:
        score = 0
        # Education match
        if any(edu in rec.lower() for edu in [education.lower() if education != 'Unknown' else '']):
            score += 3
        # Employment match
        if any(work in rec.lower() for work in [work_status.lower() if work_status != 'Unknown' else '']):
            score += 3
        # Age group match
        if age_group.lower() in rec.lower():
            score += 2
        # Engagement level match
        if engagement_level < 0.5 and 'outreach' in rec.lower():
            score += 2
        elif engagement_level > 1.5 and 'leadership' in rec.lower():
            score += 2
        priority_scores[rec] = score
    
    # Sort by priority score and add randomization for variety
    sorted_recommendations = sorted(priority_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Add some randomization to selection while keeping top recommendations
    import random
    if len(sorted_recommendations) >= 6:
        # Take top 2 high-scoring recommendations and randomly select 1 from next 4
        top_recommendations = [rec for rec, score in sorted_recommendations[:2]]
        remaining = [rec for rec, score in sorted_recommendations[2:6]]
        if remaining:
            top_recommendations.append(random.choice(remaining))
    elif len(sorted_recommendations) >= 3:
        # Take top 2 and randomly select 1 from remaining
        top_recommendations = [rec for rec, score in sorted_recommendations[:2]]
        remaining = [rec for rec, score in sorted_recommendations[2:]]
        if remaining:
            top_recommendations.append(random.choice(remaining))
    else:
        top_recommendations = [rec for rec, score in sorted_recommendations[:3]]
    
    # Format as a comprehensive recommendation
    if len(top_recommendations) >= 3:
        return f"{top_recommendations[0]} • {top_recommendations[1]} • {top_recommendations[2]}"
    elif len(top_recommendations) == 2:
        return f"{top_recommendations[0]} • {top_recommendations[1]}"
    elif len(top_recommendations) == 1:
        return top_recommendations[0]
    else:
        return "SDG 4: Quality Education Program • SDG 8: Decent Work Initiative • SDG 17: Partnership Building"

@main.route('/clustering_model')
@login_required
def clustering_model():
    # 1. Fetch data from the database with additional SDG-relevant features
    profiles = db.session.query(
        KKProfile.Respondent_No,
        KKProfile.Age,
        KKDemographics.Educational_Background,
        KKDemographics.Work_Status,
        KKDemographics.Attended_KK_Assembly,
        KKDemographics.Did_you_vote_last_SK_election,
        KKProfile.Sex_Assigned_by_Birth,
        KKProfile.Barangay,
        KKProfile.Region,
        KKProfile.Province,
        KKProfile.Municipality
    ).join(KKDemographics, KKProfile.Respondent_No == KKDemographics.Respondent_No).all()

    # 2. Preprocess data for clustering with SDG-focused features
    data = []
    for p in profiles:
        try:
            age = int(p.Age) if p.Age is not None and str(p.Age).isdigit() else 0
        except Exception:
            age = 0
        
        # Enhanced demographic features for SDG alignment
        education = p.Educational_Background or 'Unknown'
        work_status = p.Work_Status or 'Unknown'
        attended = 1 if p.Attended_KK_Assembly == 'Yes' else 0
        voted = 1 if p.Did_you_vote_last_SK_election == 'Yes' else 0
        sex = p.Sex_Assigned_by_Birth or 'Unknown'
        barangay = p.Barangay or 'Unknown'
        region = p.Region or 'Unknown'
        
        # Calculate SDG-relevant indicators
        # SDG 1 (Poverty): Employment status
        poverty_indicator = 0 if work_status == 'Unemployed' else 1
        
        # SDG 4 (Education): Education level
        education_level = 0
        if education in ['College graduate', 'College undergraduate']:
            education_level = 3
        elif education in ['High school graduate', 'High school undergraduate']:
            education_level = 2
        elif education in ['Elementary graduate', 'Elementary undergraduate']:
            education_level = 1
        
        # SDG 5 (Gender): Gender empowerment
        gender_empowerment = 1 if sex == 'Female' else 0
        
        # SDG 8 (Work): Economic participation
        economic_participation = attended + voted + poverty_indicator
        
        # SDG 16 (Governance): Civic engagement
        civic_engagement = attended + voted
        
        data.append([
            age, education, work_status, attended, voted, sex, barangay, region,
            poverty_indicator, education_level, gender_empowerment, 
            economic_participation, civic_engagement
        ])

    # Encode categorical features
    education_le = LabelEncoder()
    work_le = LabelEncoder()
    sex_le = LabelEncoder()
    region_le = LabelEncoder()
    
    educations = [row[1] for row in data]
    works = [row[2] for row in data]
    sexes = [row[5] for row in data]
    regions = [row[7] for row in data]
    
    education_encoded = education_le.fit_transform(educations)
    work_encoded = work_le.fit_transform(works)
    sex_encoded = sex_le.fit_transform(sexes)
    region_encoded = region_le.fit_transform(regions)

    # Enhanced feature matrix for SDG-focused clustering
    X = np.array([
        [row[0], education_encoded[i], work_encoded[i], row[3], row[4], 
         sex_encoded[i], region_encoded[i], row[8], row[9], row[10], 
         row[11], row[12]]
        for i, row in enumerate(data)
    ])

   # 3. Run KMeans clustering for event recommendation with randomization
    import random
    import time
    
    # Generate random seeds for different clustering results each time
    random_seed1 = int(time.time() * 1000) % 10000  # Use current time for randomness
    random_seed2 = random.randint(1, 1000)  # Additional randomness
    
    kmeans = KMeans(n_clusters=3, random_state=random_seed1, n_init=10).fit(X)
    labels = kmeans.labels_
    silhouette_event = silhouette_score(X, labels) if len(set(labels)) > 1 else None
    
    # Additional clustering metrics for better analysis
    from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score
    calinski_event = calinski_harabasz_score(X, labels) if len(set(labels)) > 1 else None
    davies_event = davies_bouldin_score(X, labels) if len(set(labels)) > 1 else None

    # --- Youth Needs Support with SDG Focus ---
    # SDG-focused features: poverty, education, gender, economic participation
    sdg_features = np.array([
        [row[8], row[9], row[10], row[11]]  # poverty, education, gender, economic
        for row in data
    ])
    
    kmeans2 = KMeans(n_clusters=3, random_state=random_seed2, n_init=10).fit(sdg_features)
    labels2 = kmeans2.labels_
    
    # SDG-focused cluster labels
    sdg_support_labels = ['SDG Priority Group', 'SDG Development Group', 'SDG Empowerment Group']
    needs_support_groups = []
    
    for i in range(3):
        indices = np.where(labels2 == i)[0]
        cluster_profiles = [profiles[j] for j in indices]
        count = len(cluster_profiles)
        
        # Calculate SDG-relevant metrics
        avg_poverty = np.mean([data[j][8] for j in indices])  # SDG 1
        avg_education = np.mean([data[j][9] for j in indices])  # SDG 4
        avg_gender_emp = np.mean([data[j][10] for j in indices])  # SDG 5
        avg_economic = np.mean([data[j][11] for j in indices])  # SDG 8
        
        # Determine primary SDG focus for this cluster
        sdg_focus = []
        if avg_poverty < 0.5:
            sdg_focus.append("SDG 1: Poverty Alleviation")
        if avg_education < 2:
            sdg_focus.append("SDG 4: Quality Education")
        if avg_gender_emp < 0.5:
            sdg_focus.append("SDG 5: Gender Equality")
        if avg_economic < 1.5:
            sdg_focus.append("SDG 8: Decent Work")
        
        primary_sdg = sdg_focus[0] if sdg_focus else "SDG 17: Partnerships"
        
        education_counter = Counter([p.Educational_Background for p in cluster_profiles if p.Educational_Background])
        common_education = education_counter.most_common(1)[0][0] if education_counter else '-'
        work_counter = Counter([p.Work_Status for p in cluster_profiles if p.Work_Status])
        common_employment = work_counter.most_common(1)[0][0] if work_counter else '-'
        
        needs_support_groups.append({
            "label": f"{sdg_support_labels[i]} ({primary_sdg})",
            "count": int(count),
            "avg_participation": float(round(avg_economic, 2)),
            "common_education": common_education,
            "common_employment": common_employment,
            "sdg_focus": primary_sdg
        })
    
    needs_support_chart_data = {
        "datasets": [
            {
                "label": sdg_support_labels[i],
                "data": [
                    {"x": float(sdg_features[j][0]), "y": float(sdg_features[j][1])}
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
    silhouette_support = silhouette_score(sdg_features, labels2) if len(set(labels2)) > 1 else None
    
    # Additional clustering metrics for needs support
    calinski_support = calinski_harabasz_score(sdg_features, labels2) if len(set(labels2)) > 1 else None
    davies_support = davies_bouldin_score(sdg_features, labels2) if len(set(labels2)) > 1 else None

    # 4. Prepare cluster summaries and chart data for the template
    event_clusters = []
    for i in range(3):
        indices = np.where(labels == i)[0]
        cluster_profiles = [profiles[j] for j in indices]
        count = len(cluster_profiles)
        
        # Calculate comprehensive SDG-relevant demographics
        ages = [int(p.Age) for p in cluster_profiles if p.Age is not None and str(p.Age).isdigit()]
        avg_age = np.mean(ages) if ages else 0
        
        # SDG-focused demographic analysis
        poverty_rate = np.mean([data[j][8] for j in indices])
        education_level = np.mean([data[j][9] for j in indices])
        gender_balance = np.mean([data[j][10] for j in indices])
        economic_participation = np.mean([data[j][11] for j in indices])
        civic_engagement = np.mean([data[j][12] for j in indices])
        
        # Determine primary SDG focus for recommendations
        sdg_priorities = []
        if poverty_rate < 0.5:
            sdg_priorities.append("SDG 1")
        if education_level < 2:
            sdg_priorities.append("SDG 4")
        if gender_balance < 0.5:
            sdg_priorities.append("SDG 5")
        if economic_participation < 1.5:
            sdg_priorities.append("SDG 8")
        if civic_engagement < 1:
            sdg_priorities.append("SDG 16")
        
        # Demographic counters
        sex_counter = Counter([p.Sex_Assigned_by_Birth for p in cluster_profiles if p.Sex_Assigned_by_Birth])
        top_sex = sex_counter.most_common(1)[0][0] if sex_counter else '-'
        
        education_counter = Counter([p.Educational_Background for p in cluster_profiles if p.Educational_Background])
        work_counter = Counter([p.Work_Status for p in cluster_profiles if p.Work_Status])
        
        top_education = education_counter.most_common(1)[0][0] if education_counter else 'Unknown'
        top_work = work_counter.most_common(1)[0][0] if work_counter else 'Unknown'
        
        # Calculate engagement level
        avg_attended = np.mean([1 if p.Attended_KK_Assembly == 'Yes' else 0 for p in cluster_profiles])
        avg_voted = np.mean([1 if p.Did_you_vote_last_SK_election == 'Yes' else 0 for p in cluster_profiles])
        engagement_level = avg_attended + avg_voted
        
        # Determine age group
        if avg_age < 18:
            age_group = 'Teen'
        elif avg_age < 25:
            age_group = 'Young Adult'
        else:
            age_group = 'Adult'
        
        # Intelligent recommendation logic with SDG focus
        recommended_event = get_intelligent_recommendation(
            top_education, top_work, top_sex, age_group, engagement_level, avg_age
        )
        
        # Create detailed demographic summary with SDG indicators
        demo_summary = f"Avg Age: {avg_age:.1f} • {top_sex}"
        if education_counter:
            top_edu = list(education_counter.keys())[0]
            demo_summary += f" • {top_edu}"
        if work_counter:
            top_work = list(work_counter.keys())[0]
            demo_summary += f" • {top_work}"
        
        # Add SDG focus to summary
        if sdg_priorities:
            demo_summary += f" • Focus: {', '.join(sdg_priorities[:2])}"
        
        # Dynamic cluster labels based on SDG characteristics
        if engagement_level > 1.5 and education_level > 2:
            label = random.choice(["SDG Leadership Circle", "SDG Innovation Group", "SDG Empowerment Network"])
        elif poverty_rate < 0.5 and education_level < 2:
            label = random.choice(["SDG Development Cluster", "SDG Support Network", "SDG Growth Initiative"])
        else:
            label = random.choice(["SDG Community Group", "SDG Opportunity Circle", "SDG Partnership Network"])
        
        event_clusters.append({
            "label": label,
            "count": int(count),
            "top_demo": demo_summary,
            "top_engagement": f"Economic: {economic_participation:.1f} • Civic: {civic_engagement:.1f}",
            "recommended_event": recommended_event,
            "avg_age": round(avg_age, 1),
            "engagement_level": round(engagement_level, 2),
            "sdg_focus": ', '.join(sdg_priorities[:3]) if sdg_priorities else "SDG 17"
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

    return render_template(
        'clustering_model.html',
        event_clusters=event_clusters,
        event_cluster_chart_data=event_cluster_chart_data,
        needs_support_groups=needs_support_groups,
        needs_support_chart_data=needs_support_chart_data,
        silhouette_event=silhouette_event,
        silhouette_support=silhouette_support,
        calinski_event=calinski_event,
        davies_event=davies_event,
        calinski_support=calinski_support,
        davies_support=davies_support
    )


