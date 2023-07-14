import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from wtforms import Form, StringField,PasswordField, validators

cur_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(cur_dir, "testdb.sqlite3")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# ----------------------------------------------------------------------------------------------------------------
db = SQLAlchemy()
db.init_app(app)  #initializing db app
app.app_context()  #pushing into the context

# database models
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(1000), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10),nullable=False, default='user')

    def get_id(self):
        return str(self.user_id)

class Venue(db.Model):
    __tablename__ = 'venue'
    venue_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    venue_name = db.Column(db.String(100), nullable=False)
    place = db.Column(db.String(1000), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

class Show(db.Model):
    __tablename__ = 'show'
    show_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    show_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(100), nullable=False)
    ticket_available = db.Column(db.Integer)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.venue_id'), nullable=False)
    venue = db.relationship('Venue', backref=db.backref('show', lazy=True))

class Ticket(db.Model):
    __tablename__ = 'ticket'
    ticket_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    num_ticket = db.Column(db.Integer, nullable=False)
    show_name = db.Column(db.String)
    place = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    user = db.relationship('User', backref=db.backref('ticket', lazy=True))

    show_id = db.Column(db.Integer, db.ForeignKey('show.show_id'), nullable=False)
    show = db.relationship('Show', backref=db.backref('ticket', lazy=True))

# ----------------------------------------------------------------------------------------------------------------

#validators
class UserForm(Form):
    username = StringField('username', validators=[validators.InputRequired()])
    email = StringField('email', validators=[validators.InputRequired()])
    password = PasswordField('password', validators=[validators.InputRequired()])

class VenueForm(Form):
    venue_name = StringField('venue_name', validators=[validators.DataRequired()])
    place = StringField('place', validators=[validators.DataRequired()])
    capacity = StringField('capacity', validators=[validators.DataRequired()])

class ShowForm(Form):
    show_name = StringField('show_name', validators=[validators.DataRequired()])
    venue_name = StringField('venue_name', validators=[validators.DataRequired()])
    rating = StringField('rating', validators=[validators.DataRequired()])
    price = StringField('price', validators=[validators.DataRequired()])
    date = StringField('date', validators=[validators.DataRequired()])
    time = StringField('time', validators=[validators.DataRequired()])

# ----------------------------------------------------------------------------------------------------------------

# configuring and initializing LoginManager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# load user object from the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------------------------------------------------------------------------------------------------

# function to be executed before each request
# delete shows that are ended from the database
@app.before_request
def delete_ended_show():
    today = datetime.now()

    shows = Show.query.all()
    for show in shows:
        dt = datetime.strptime(show.date, "%Y-%m-%d")
        if today > dt:
            db.session.delete(show)
    db.session.commit()


# route for index page
@app.route('/')
def index():
    shows = Show.query.all()
    return render_template('index.html', show_all=shows)

# route for user profile
@app.route('/profile')
@login_required
def profile():
    tickets = Ticket.query.all()
    return render_template('profile.html', tickets=tickets, name=current_user.username)

# ----------------------------------------------------------------------------------------------------------------

# routes for ticket
@app.route('/book_ticket/<int:show_id>', methods=['GET', 'POST'])
@login_required
def book_ticket(show_id):
    if request.method == 'POST':
        num_ticket = request.form.get('num_ticket')

        show = Show.query.filter_by(show_id=show_id).first()

        if int(num_ticket) > show.ticket_available:
            flash('Not enough ticket available.')
            show = Show.query.filter_by(show_id=show_id).first()
            return render_template('book_ticket.html',show=show)
        
        ticket = Ticket(num_ticket=num_ticket,show_name=show.show_name, place=show.venue.place, user_id=current_user.user_id, show_id=show_id)

        show.ticket_available -= int(num_ticket)

        db.session.add(ticket)
        db.session.commit()

        return redirect(url_for('profile'))

    show = Show.query.filter_by(show_id=show_id).first()
    return render_template('book_ticket.html', show=show, name=current_user.username)


@app.route('/cancel_ticket/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def cancel_ticket(ticket_id):
    ticket = Ticket.query.filter_by(ticket_id = ticket_id).first()
    if ticket:
        show = Show.query.filter_by(show_id = ticket.show_id).first()
        show.ticket_available += ticket.num_ticket

        db.session.delete(ticket)
        db.session.commit()

        flash('Ticket cancelled successfully.')
        return redirect(url_for('profile'))

    return redirect(url_for('profile'))

# ----------------------------------------------------------------------------------------------------------------

# route for admin dashboard
@app.route('/dashboard')
def dashboard():
    users = User.query.all()
    venues = Venue.query.all()
    shows = Show.query.all()
    tickets = Ticket.query.all()
    return render_template('dashboard.html', users=users ,venues=venues, shows=shows, tickets=tickets)

# ----------------------------------------------------------------------------------------------------------------

# route for venues
@app.route('/add_venue', methods=['GET', 'POST'])
@login_required
def add_venue():
    if request.method == 'POST':
        form = VenueForm(request.form)
        if form.validate():
            venue_name = form.venue_name.data
            place = form.place.data
            capacity = form.capacity.data

            venue = Venue.query.filter_by(venue_name=venue_name).first()
            if venue:
                flash('Venue already exist')
                return redirect(url_for('dashboard'))

            venue = Venue(venue_name=venue_name, place=place, capacity=capacity)

            db.session.add(venue)
            db.session.commit()

            flash('Venue added succesfully....')
            return redirect(url_for('dashboard'))
        
        flash('Invalid data format')
        return render_template('add_venue.html')
    
    return render_template('add_venue.html')


@app.route('/edit_venue/<int:venue_id>', methods=['GET', 'POST'])
@login_required
def edit_venue(venue_id):
    if request.method == 'POST':
        form = VenueForm(request.form)
        if form.validate():
            venue_name = form.venue_name.data
            place = form.place.data
            capacity = form.capacity.data

            venue = Venue.query.get(venue_id)
            venue.venue_name = venue_name
            venue.place = place
            venue.capacity = capacity

            db.session.commit()
            flash('Venue with venue_id ' + str(venue.venue_id) + ' is successfully edited....')
            return redirect(url_for('dashboard'))
        
        flash('Invalid data format')
        venue = Venue.query.get(venue_id)
        return render_template('edit_venue.html', venue=venue)
        
    venue = Venue.query.get(venue_id)
    return render_template('edit_venue.html', venue=venue)


@app.route('/delete_venue/<int:venue_id>', methods=['GET', 'POST'])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if venue:
        db.session.delete(venue)
        db.session.commit()
        flash('Venue with venue_id ' + str(venue_id) + ' is removed successfully.')
        return redirect(url_for('dashboard'))
    

# routes for shows
@app.route('/add_show', methods=['GET', 'POST'])
@login_required
def add_show():
    if request.method == 'POST':
        form = ShowForm(request.form)
        if form.validate():
            show_name = form.show_name.data
            venue_name = form.venue_name.data
            rating = form.rating.data
            price = form.price.data
            date = form.date.data
            time = form.time.data
            
            venue = Venue.query.filter_by(venue_name=venue_name).first()
            if venue:
                venue_id = venue.venue_id
                ticket_available = venue.capacity

                show = Show(show_name=show_name, rating=rating, price=price, date=date, time=time, ticket_available=ticket_available, venue_id=venue_id)

                db.session.add(show)
                db.session.commit()

                flash('Show successfully created...')
                return redirect(url_for('dashboard'))
    
        flash('Invalid data format. Please enter data in required format')
        venue = Venue.query.all()
        return render_template('add_show.html', venues=venue)
        
    venue = Venue.query.all()
    return render_template('add_show.html', venues=venue)


@app.route('/edit_show/<int:show_id>', methods=['GET', 'POST'])
@login_required
def edit_show(show_id):
    if request.method == 'POST':
        show_name = request.form.get('show_name')
        price = request.form.get('price')
        date = request.form.get('date')
        time = request.form.get('time')
        venue_name = request.form.get('venue_name')

        venue = Venue.query.filter_by(venue_name=venue_name).first()
        if venue:
            venue_id = venue.venue_id
            ticket_available = venue.capacity

        show = Show.query.get(show_id)
        show.show_name = show_name
        show.price = price
        show.date = date
        show.time = time
        show.venue_id = venue_id
        show.ticket_available = ticket_available

        db.session.commit()
        flash('Show with show_id ' + str(show_id) + ' is successfully edited.')
        return redirect(url_for('dashboard'))

    venues = Venue.query.all()
    show = Show.query.get(show_id)
    return render_template('edit_show.html', show=show, venues=venues)


@app.route('/delete_show/<int:show_id>', methods=['GET', 'POST'])
@login_required
def delete_show(show_id):
    show = Show.query.get(show_id)
    if show:
        db.session.delete(show)
        db.session.commit()
        flash('show with the show_id ' + str(show_id) + ' is removed successfully.')
        return redirect(url_for('dashboard'))

# ----------------------------------------------------------------------------------------------------------------

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():    
    if request.method =='POST':
        username = request.form.get('username')
        password = request.form.get('password')    
    
        user = User.query.filter_by(username=username).first()

        if user and (user.password == password):
            login_user(user)
            
            if user.role == 'admin':
                # redirect to admin panel
                return redirect(url_for('dashboard'))
            else:
                # redirect to home page
                return redirect(url_for('index'))

        else:
            flash('Please check your login credential and try again')
            return redirect(url_for('login'))
            
    return render_template('login.html')


# ----------------------------------------------------------------------------------------------------------------

#Sign up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        form = UserForm(request.form)
        if form.validate():
            username = form.username.data
            email = form.email.data
            password = form.password.data

            existing_user = User.query.filter_by(email=email).first()

            if existing_user:
                flash('Email address already exists.')
                return redirect(url_for('signup'))

            new_user = User(username=username, email=email, password=password)

            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login'))
        
        flash('Invalid data format. Please try again.')
        return render_template('signup.html')

    return render_template('signup.html')

# ----------------------------------------------------------------------------------------------------------------

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ----------------------------------------------------------------------------------------------------------------

app.run(debug=True)