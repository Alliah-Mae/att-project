# app/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import KKProfile, User
from app.forms import LoginForm, RegistrationForm
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import distinct
from sqlalchemy import text

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


