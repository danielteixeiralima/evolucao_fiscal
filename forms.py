from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6)
    ])
    password2 = PasswordField('Repeat Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    is_admin = BooleanField('Administrator')
    submit = SubmitField('Create User')
    
    def __init__(self, original_username=None, original_email=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Username already exists.')
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Email already registered.')

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    is_admin = BooleanField('Administrator')
    submit = SubmitField('Update User')
    
    def __init__(self, original_username=None, original_email=None, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Username already exists.')
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Email already registered.')

class FileUploadForm(FlaskForm):
    file = FileField('Excel File', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Only Excel files (.xlsx, .xls) are allowed!')
    ])
    description = TextAreaField('Description (Optional)')
    submit = SubmitField('Upload File')
