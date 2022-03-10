from signaturelib import services
import os
from flask import Flask, flash, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField
from wtforms.validators import InputRequired, Length, ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

UPLOAD_FOLDER = 'media/uploads'

app = Flask(__name__)
db = SQLAlchemy(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'mysecretkeyshhh'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.jinja_env.filters['zip'] = zip

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(40), nullable=True, unique=True)
    username = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(20), nullable=True)
    id_api = db.Column(db.Integer, nullable=True, unique=True)


db.create_all()


class RegisterForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(
        min=4, max=80)], render_kw={"placeholder": "Name", "class": "form-control form-control-user"})
    email = StringField(validators=[InputRequired(), Length(
        min=4, max=40)], render_kw={"placeholder": "Email", "class": "form-control form-control-user"})
    username = StringField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Username", "class": "form-control form-control-user"})
    password = PasswordField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Password", "class": "form-control form-control-user"})
    submit = SubmitField("Register", render_kw={
                         "class": "btn btn-primary btn-user btn-block"})

    def validate_email(self, email):
        existing_user_email = User.query.filter_by(email=email.data).first()
        if existing_user_email:
            raise ValidationError("that email already exists!!!")


class LoginForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Length(
        min=4, max=40)], render_kw={"placeholder": "Email"})
    password = PasswordField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


class SignatureRequestUserForm(FlaskForm):
    user = SelectField(
        render_kw={"placeholder": "User", "class": "form-control form-control-user"})
    pos_x = IntegerField(render_kw={
                         "placeholder": "Position X", "class": "form-control form-control-user"})
    pos_y = IntegerField(render_kw={
                         "placeholder": "Position Y", "class": "form-control form-control-user"})
    num_page = IntegerField(render_kw={
                            "placeholder": "Page Number", "class": "form-control form-control-user"})
    submit = SubmitField("Send", render_kw={
                         "class": "btn btn-primary btn-user btn-block"})

    def __init__(self):
        super(SignatureRequestUserForm, self).__init__()
        self.user.choices = [(u.full_name) for u in services.list_users()]


@app.route('/')
@login_required
def home():
    return redirect(url_for('get_requests_signature'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit:
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('home'))
    return render_template('login.html', form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        users = services.list_users()
        for user in users:
            if user.email == form.email.data:
                id_api = user.id
        if not id_api:
            api_user = services.register_user(
                name=form.name.data, email=form.email.data, username=form.username.data, password=form.password.data)
            id_api = api_user.id
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(name=form.name.data, email=form.email.data,
                        username=form.username.data, password=hashed_password, id_api=id_api)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('upload_signature'))
    return render_template('register.html', form=form)


@app.route('/uploadSignature', methods=['GET', 'POST'])
@login_required
def upload_signature():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file.save(os.path.join(
                app.config['UPLOAD_FOLDER'], file.filename))
            if services.validate_signature(app.config['UPLOAD_FOLDER'] + '/' + file.filename):
                services.insert_signature(current_user.id_api, file.filename, os.path.join(
                    app.config['UPLOAD_FOLDER'], file.filename))
                return redirect(url_for('profile'))
            else:
                flash('that imagen is not a signature', 'danger')
    return render_template('uploadSignature.html')


@app.route('/profile')
@login_required
def profile():
    image = services.get_file(services.get_user(current_user.id_api).signature)
    if not image:
        return render_template('profile.html', img_data='https://sankosf.com/wp-content/themes/gecko/assets/images/placeholder.png')
    return render_template('profile.html', img_data=image.file)


@app.route('/registerRequestSignature', methods=['GET', 'POST'])
@login_required
def register_request_signature():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file.save(os.path.join(
                app.config['UPLOAD_FOLDER'], file.filename))
            services.register_request_signature(current_user.id_api, file.filename, os.path.join(
                app.config['UPLOAD_FOLDER'], file.filename), request.form.get('subject'))
            return render_template('home.html')
    return render_template('registerRequestSignature.html')


@app.route('/getRequestsSignature')
@login_required
def get_requests_signature():
    requests = services.get_request_signature_by_user(current_user.id_api)
    for request in requests:
        request.document = services.get_file(request.document).name
    return render_template('requestsSignature.html', requests=requests)


@app.route('/registerRequestSignatureUser', methods=['GET', 'POST'])
@login_required
def register_request_signature_user():
    form = SignatureRequestUserForm()
    if form.validate_on_submit():
        users = services.list_users()
        for user in users:
            if user.full_name == form.user.data:
                id_user = user.id
        services.register_request_signature_user(request.args.get(
            'id'), id_user, form.pos_x.data, form.pos_y.data, form.num_page.data)
        return redirect(url_for('home'))
    return render_template('signatureRequestUser.html', form=form)


@app.route('/getListSignatureRequests', methods=['GET', 'POST'])
@login_required
def get_list_signature_request_user_by_user_id():
    requests = services.get_list_signature_request_user_by_user_id_and_signed(
        current_user.id_api, True)
    requests.extend(services.get_list_signature_request_user_by_user_id_and_signed(
        current_user.id_api, False))
    data = list()
    for request in requests:
        data.append([services.get_user(request.user).full_name, services.get_file(
            services.get_signature_request(request.request).document).name])
    return render_template('listSignatureRequests.html', requests=requests, data=data)


@app.route('/approveSignature', methods=['GET', 'POST'])
@login_required
def approve_signature():
    services.approve_signature(request.args.get('id'))
    return redirect(url_for('get_list_signature_request_user_by_user_id'))


@app.route('/getListSignatureDocuments', methods=['GET', 'POST'])
@login_required
def get_list_signature_request_user_by_request_id_and_signed():
    requests = services.get_list_signature_request_user_by_request_id_and_signed(
        request.args.get('id'), True)
    requests.extend(services.get_list_signature_request_user_by_request_id_and_signed(
        request.args.get('id'), False))
    data = list()
    for r in requests:
        data.append([services.get_user(r.user).full_name, services.get_file(
            services.get_signature_request(r.request).document).name])
    return render_template('listSignatureDocuments.html', requests=requests, data=data)


if __name__ == '__main__':
    app.run(debug=True)
