import os
import secrets
from datetime import datetime
from PIL import Image
from flask import render_template as rt, request, redirect, url_for, flash,send_from_directory
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import or_
from doctor import app, db, bcrypt
from doctor.helper import diagnose_text, dcnn
from doctor.models import User, Patient, Patient_ctimages as PatientDetails,Patient_analysis as PatientAnalysis, Chat, Request
from doctor.forms import RegistrationForm, LoginForm, UpdateAccountForm, PatientForm
from humanize import naturaltime

# admin array
admin = ['admin', 'admin@gmail.com']

# home page start
@app.route('/')
@app.route('/home')
def index():
    return rt("home.html", check_request=check_request)
# home page end

# chat start
@app.route('/new_message/<int:sender_id>/<int:receiver_id>', methods=['GET','POST'])
def new_message(sender_id, receiver_id):
    message = request.form.get('message')
    if message != '':
        chat = Chat(sender_id=sender_id, receiver_id=receiver_id,message=message)
        db.session.add(chat)
        db.session.commit()
        return redirect(url_for('preview_chat',sender_id=sender_id,receiver_id=receiver_id))
def date_to(d):
    return d.strftime('%I:%M %p')

@app.route('/preview_chat/<int:sender_id>/<int:receiver_id>')
def preview_chat(sender_id, receiver_id):
    messages = Chat.query.filter(
        or_(
            (Chat.sender_id == sender_id) & (Chat.receiver_id == receiver_id),
            (Chat.sender_id == receiver_id) & (Chat.receiver_id == sender_id)
        ),
    ).all()

    user = User.query.get_or_404(receiver_id)
    return rt('chat/index.html', messages=messages, check_request=check_request, user=user, sender_id=sender_id, receiver_id=receiver_id, diffHumans=naturaltime, date_to=date_to)
# chat end

# REQUESTS START
@app.route("/check_request_/<int:user_id>")
def check_request_(user_id):
    request = Request.query.filter_by(requester_id=user_id).all()
    return request

@app.route("/check_request/<int:user_id>")
def check_request(user_id):
    request = Request.query.filter_by(receiver_id=user_id).all()
    return request

@app.route("/toggle_request/<int:user_id>", methods=['POST'])
def toggle_request(user_id):
    receiver = User.query.get_or_404(user_id)
    request = Request.query.filter_by(requester=current_user, receiver=receiver).first()

    if request:
        # If request exists, remove it
        db.session.delete(request)
        db.session.commit()
        flash('Request canceled successfully', 'success')
    else:
        # If request doesn't exist, create it
        request = Request(requester=current_user, receiver=receiver)
        db.session.add(request)
        db.session.commit()
        flash('Request sent successfully', 'success')

    return redirect(url_for('doctorlist'))

@app.route('/requests', methods=['GET','POST'])
def requests(): 
    id = current_user.id
    data = Request.query.filter_by(status='pending', receiver_id=id).all()
    return rt("requests/index.html", data=data , check_request=check_request)

@app.route('/requests/<int:receiver_id>/<int:requester_id>/<status>', methods=['GET','POST'])
def request_(receiver_id, requester_id, status):
    request = Request.query.filter_by(receiver_id=receiver_id, requester_id=requester_id).first_or_404()
    if request:
        request.status = status
        db.session.commit()

    return redirect(url_for('requests'))
# REQUESTS END

# analysis start
@app.route('/users/<int:id>/analysis_patients', methods=['GET', 'POST'])
@login_required
def analysis_patients(id):
    if check_is_authenticated(id):
        page = request.args.get('page', 1, type=int)
        patients = Patient.query.filter_by(user_id=id).order_by(Patient.date.desc()).paginate(page=page, per_page=10)
        return rt("analysis/index.html", patients=patients,check_request=check_request)
    else:
        return redirect(url_for('index'))
@app.route('/delete_analysis_pdf/<int:id>/<path:path>')
@login_required
def delete_analysis_pdf(id, path):
    try:
        patient_analysis = PatientAnalysis.query.filter_by(id=id, file=path).first_or_404()
        db.session.delete(patient_analysis)
        db.session.commit()
        delete_image(path, 'static/files_analysis')
    except Exception as e:
        print(e)
        return redirect(url_for('analysis_actions', patient_id=patient_analysis.patient_id, check_request=check_request))
    return redirect(url_for('analysis_actions', patient_id=patient_analysis.patient_id,check_request=check_request))


@app.route('/users/<int:patient_id>/analysis_actions', methods=['GET', 'POST'])
@login_required
def analysis_actions(patient_id):
    try:
        patient = Patient.query.filter_by(id=patient_id).first_or_404()
        patient_analysis = []

        try:
            patient_analysis = PatientAnalysis.query.filter_by(patient_id=patient_id).all()
            return rt('analysis/actions.html', patient=patient, patient_analysis=patient_analysis, check_request=check_request)
        except Exception as e :
            patient_analysis = []
        return rt('analysis/actions.html', patient=patient, patient_analysis=patient_analysis,check_request=check_request)

    except Exception as e :
        return redirect(url_for('index'))

@app.route('/users/<int:patient_id>/analysis_patients/upload', methods=['GET', 'POST'])
@login_required
def analysis_patients_upload(patient_id):
    if request.method == 'POST':
        dir = 'doctor/static/files_analysis/'

        file = request.files['analysis_file']

        analysis_name = request.form.get('analysis_name')
        
        if file.filename == '':
            flash('No selected file', 'danger')
        try:
            if file and file.filename.endswith('.pdf'):
                random_hex = secrets.token_hex(8)
                _, f_ext = os.path.splitext(file.filename)
                path = random_hex + f_ext
                file.save(dir + path)

                patient_analysis = PatientAnalysis()
                patient_analysis.file = path
                patient_analysis.name = analysis_name
                patient_analysis.patient_id = patient_id

                db.session.add(patient_analysis)
                db.session.commit()
                return redirect(url_for('analysis_actions', patient_id=patient_id))
        except Exception as e:
            return redirect(url_for('analysis_actions', patient_id=patient_id))
# analysis end

# ct images start
@app.route('/delete_ctimage/<int:patient_id>/<path>', methods=['GET', 'POST'])
@login_required
def delete_ctimage(patient_id, path):
    patient_details = PatientDetails.query.filter_by(patient_id=patient_id, image_file=path).first_or_404()

    db.session.delete(patient_details)
    db.session.commit()

    delete_image(path)
    return redirect(url_for('ctimage_actions', patient_id=patient_id, id=current_user.id))

@app.route('/users/<int:id>/patients/<int:patient_id>/ctimage_actions/')
@login_required
def ctimage_actions(patient_id,id):
    if check_is_authenticated(id):
        patient = Patient.query.filter_by(id=patient_id).first_or_404()
        return rt('ct_images/actions.html', patient=patient, check_request=check_request)
    else:
        return redirect(url_for('index'))
    
@app.route('/users/<int:id>/ct_image/uploads', methods=['POST'])
@login_required
def ct_image_uploads(id):
    try:
        uploaded_files = request.files.getlist("images")
        for img in uploaded_files:
            patient_details = PatientDetails()
            patient_details.patient_id = id
            pic_path = save_picture_test(img)
            path = 'doctor/static/test_img/' + pic_path
            result = dcnn(path)
            diagnosis = diagnose_text(result)
            patient_details.image_file = pic_path
            patient_details.result = result
            patient_details.diagnosis = diagnosis
            db.session.add(patient_details)
            db.session.commit()
        return redirect(url_for('ctimage_actions', patient_id=id, id=current_user.id))

    except Exception as e:
        flash('No files uploaded!', 'danger')
        return redirect(url_for('ctimage_actions', patient_id=id, id=current_user.id))

@app.route('/delete_image/<path:path>', methods=['GET'])
def delete_image(path, dir='static/test_img'):
    try:
        image_path = os.path.join(app.root_path, dir, path)
        
        if os.path.exists(image_path):
            os.remove(image_path)
            return 'Image deleted successfully', 200
    except Exception as e:
        return str(e), 500

@app.route('/users/<int:id>/ct_image')
@login_required
def ct_image(id):
    if check_is_authenticated(id):
        page = request.args.get('page', 1, type=int)
        patients = Patient.query.filter_by(user_id=id).order_by(Patient.date.desc()).paginate(page=page, per_page=10)
        return rt("ct_images/index.html", patients=patients, check_request=check_request)
    else:
        return redirect(url_for('index'))
# ct images end

# doctors start
@app.route("/preview_data/<int:user_id>")
def preview_data(user_id):
    user = User.query.get_or_404(user_id)
    request = Request.query.filter_by(receiver_id=current_user.id, requester_id=user_id).first_or_404()
    return rt("doctors/preview_data.html", request=request,check_request=check_request, user=user)

@app.route('/doctors')
def doctorlist():
    doctors = User.query.order_by(User.id).all()
    patient_details = PatientDetails.query.order_by(PatientDetails.created_at).all()
    return rt("doctors/index.html", doctors=doctors, patient_details=patient_details, check_request=check_request,  get_request=get_request, check_request_exists=check_request_exists)
# doctors end
    
# auth start
@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture_profile(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_img/' + current_user.image_file)
    return rt('auth/account.html', title='Account', image_file=image_file, form=form, check_request=check_request)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Welcome! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return rt('auth/register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    return rt('auth/login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))
# auth end

# logic start
def check_is_authenticated(id):
    global admin
    if current_user.username in admin or current_user.email in admin:
        return True
    if current_user.id  == id:
        return True
    else:
        flash('you are not provided to access that page..', 'danger')
        return False
        
@app.route('/view_pdf/<path:filename>')
def view_pdf(filename):
    directory = 'static/files_analysis'
    return send_from_directory(directory, filename)

@app.route('/x/xxxx/<int:user_id>/<int:doctor_id>')
def check_request_exists(doctor_id, user_id):
    requests = get_all_requests_for_user(user_id)
    for request in requests:
        if request.receiver_id == doctor_id:
            return True
    return False

@app.route('/x/xx/<int:user_id>/<int:doctor_id>')
def get_request(doctor_id, user_id):
    requests = get_all_requests_for_user(user_id)
    for request in requests:
        if request.receiver_id == doctor_id:
            return request
    return None

@app.route('/x/x/<int:user_id>')
def get_all_requests_for_user(user_id):
    requests = Request.query.filter_by(requester_id=user_id).all()
    return requests 

def save_picture_profile(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_img', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

def save_picture_test(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/test_img', picture_fn)

    i = Image.open(form_picture)
    i.save(picture_path)
    return picture_fn
# logic end

# diagnosis start
@app.route('/diagnosis/<int:user_id>')
@login_required
def diagnosises(user_id):
    if check_is_authenticated(user_id):
        page = request.args.get('page', 1, type=int)
        patients = Patient.query.filter_by(user_id=user_id).order_by(Patient.date.desc()).paginate(page=page, per_page=10)
        return rt("diagnosis/all.html", patients=patients, diffHumans=naturaltime, check_request=check_request)
    else:
        return redirect(url_for('index'))

@app.route('/diagnosis')
@login_required
def diagnosis():
    page = request.args.get('page', 1, type=int)
    patients = Patient.query.order_by(Patient.date.desc()).paginate(page=page, per_page=10)
    return rt("diagnosis/index.html", patients=patients, diffHumans=naturaltime, check_request=check_request)
# diagnosis end

# patients start
@app.route('/user/<int:id>/patients')
@login_required
def my_patients(id):
    if check_is_authenticated(id):
        page = request.args.get('page', 1, type=int)
        patients = Patient.query.filter_by(user_id=id).order_by(Patient.date.desc()).paginate(page=page, per_page=10)
        return rt("patients/index.html", patients=patients, check_request=check_request)
    else:
        return redirect(url_for('index'))

@app.route('/patient/new', methods=['GET', 'POST'])
@login_required
def new_patient():
    form = PatientForm()
    if form.validate_on_submit():
        existing_patient = Patient.query.filter_by(firstname=form.firstname.data, lastname=form.lastname.data).first()
        mail = form.email.data
        phone = form.phone.data
        birth_date = form.birth_date.data
        if existing_patient != None:
            mail = existing_patient.email
            phone = existing_patient.phone
            birth_date = existing_patient.birth_date
        patient = Patient(firstname=form.firstname.data, lastname=form.lastname.data,
                          birth_date = birth_date, phone=phone, email=mail,doctor=current_user)
        db.session.add(patient)
        db.session.commit()
        flash('New patient added!', 'success')
        return redirect(url_for('diagnosis'))
    return rt('patients/create.html', title='New Patient', form=form, legend='New Patient', check_request=check_request)

@app.route("/users/<int:id>/patient/<int:patient_id>")
@login_required
def patient(patient_id, id):
    if check_is_authenticated(id):
        patient = Patient.query.get_or_404(patient_id)
        return rt('patients/show.html', title=patient.firstname, patient=patient,diffHumans=naturaltime)
    else:
        return redirect(url_for('index'))
# patients end

# chart
@app.route('/chart')
def chart():
    return rt('chart/index.html', check_request=check_request)

# chatbot
@app.route('/jarvis')
def jarvis():
    return rt('chat/jarvis.html', title=jarvis, check_request=check_request)

if __name__ == '__main__':
    app.run(debug=True)