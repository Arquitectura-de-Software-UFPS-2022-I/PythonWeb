import re
from signaturelib import services

import os

from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError

UPLOAD_FOLDER = 'media/uploads'

app = Flask(__name__)
db = SQLAlchemy(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'mysecretkeyshhh'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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


@app.route('/')
@login_required
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit:
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if user.password == form.password.data:
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
        api_user = services.register_user(
            name=form.name.data, email=form.email.data, username=form.username.data, password=form.password.data)

        new_user = User(name=api_user.full_name, email=api_user.email,
                        username=api_user.username, password=api_user.password, id_api=api_user.id)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html', form=form)


@app.route('/uploadSignature', methods=['GET', 'POST'])
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
            return render_template('uploadSignature.html')
    return render_template('uploadSignature.html')


@app.route('/profile')
def profile():
    image = services.get_file(services.get_user(current_user.id_api).signature)
    return render_template('profile.html', img_data=image.file)


@app.route('/registerRequestSignature', methods=['GET', 'POST'])
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
def get_requests_signature():
    requests = services.get_request_signature_by_user(current_user.id_api)
    return render_template('requestsSignature.html', requests=requests)


if __name__ == '__main__':
    app.run(debug=True)


'''

'''
