from datetime import datetime
from doctor import db, login_manager
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from alembic import op

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    patients = db.relationship('Patient', backref='doctor', lazy=True)
    user = db.relationship('Request', backref='user', lazy=True, foreign_keys='Request.requester_id')
    user_receiver = db.relationship('Request', backref='user_receiver', lazy=True, foreign_keys='Request.receiver_id')

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(20), unique=False, nullable=False)
    lastname = db.Column(db.String(20), unique=False, nullable=False)
    phone = db.Column(db.String(20), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    birth_date = db.Column(db.DateTime, nullable=True)  # Add birth_date field
    file = db.Column(db.String(25), nullable=True)
    # Define the relationship to Patient_ctimages
    ct_images = relationship('Patient_ctimages', backref='patient', lazy=True, cascade="all, delete-orphan")
    analysis = db.relationship('Patient_analysis', backref='patient', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Patient('{self.firstname} {self.lastname}', '{self.phone}', '{self.email}', " \
               f"'{self.user_id}')"

class Patient_ctimages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    image_file = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    result = db.Column(db.String(20), nullable=True)
    diagnosis = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"Patient('{self.image_file}', '{self.result}', '{self.patient_id}', '{self.diagnosis}')"

class Patient_analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    file = db.Column(db.String(25), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"Patient('{self.id}', '{self.file}', '{self.patient_id}' , '{self.name}')"

class SharedData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    current_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')

    # Define relationship with User model
    current_user = db.relationship('User', foreign_keys=[current_user_id])

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')

    requester = db.relationship('User', foreign_keys=[requester_id], backref='requests_sent')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='requests_received')
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)

    # patient = db.relationship('Patient', backref='chats')

    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sender_ = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver_ = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
