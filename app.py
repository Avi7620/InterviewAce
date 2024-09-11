from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

import google.generativeai as genai

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appp.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure the generative AI API key
genai.configure(api_key="AIzaSyADC3LpYQc4SNVQPM0OuoM_NaOC_b1iRys")

# Define the generation configuration for the model
generation_config = {
    "temperature": 0.9,
    "top_p": 1, 
    "top_k": 1, 
    "max_output_tokens": 1000,
}

# Define the safety settings for content generation
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    }
]

# Create an instance of the generative model
model = genai.GenerativeModel(model_name="gemini-pro",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Question model
from datetime import datetime

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # New field


# Answer model
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(500), nullable=False)

# From Submission
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('m.html')

@app.route('/sl')
def sl():
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('m.html')

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    new_contact = Contact(name=name, email=email, message=message)
    db.session.add(new_contact)
    db.session.commit()

    flash('Your message has been sent successfully!', 'success')
    return redirect(url_for('form'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        reenter_password = request.form.get('reenter_password')

        if password != reenter_password:
            flash('Passwords do not match!')
            return redirect(url_for('signup'))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))  # Ensure this redirects to the login page

    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, password=password).first()

        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check your credentials.')
            return redirect(url_for('login'))
    
    return render_template('index.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.clear()  # Clear the session
    
    return redirect(url_for('index'))  # Redirect to the homepage or login page


@app.route('/main')
@login_required
def dashboard():
    questions = Question.query.filter_by(user_id=current_user.id).all()
    return render_template('main.html', questions=questions)

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    question_text = request.form['question']
    prompt_parts = [f"Generate 5 related questions for: {question_text}"]
    response = model.generate_content(prompt_parts)
    questions = response.text.split('\n')

    for q in questions:
        if q.strip():
            new_question = Question(text=q.strip(), user_id=current_user.id)
            db.session.add(new_question)
    
    db.session.commit()
    return redirect(url_for('questions'))  # Redirect to the questions page


@app.route('/questions')
@login_required
def questions():
    questions = Question.query.filter_by(user_id=current_user.id).all()
    
    # Group questions by timestamp
    grouped_questions = {}
    for question in questions:
        timestamp_str = question.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        if timestamp_str not in grouped_questions:
            grouped_questions[timestamp_str] = []
        grouped_questions[timestamp_str].append(question)
    
    return render_template('questions.html', grouped_questions=grouped_questions)



@app.route('/answer/<int:question_id>', methods=['GET', 'POST'])
@login_required
def answer(question_id):
    question = Question.query.get_or_404(question_id)
    if request.method == 'POST':
        answer_text = request.form['answer']
        new_answer = Answer(question_id=question.id, text=answer_text)
        db.session.add(new_answer)
        db.session.commit()
        return redirect(url_for('questions'))
    return render_template('answer.html', question=question)

@app.route('/view/<int:question_id>', methods=['GET'])
@login_required
def view_question(question_id):
    question = Question.query.get_or_404(question_id)
    answers = Answer.query.filter_by(question_id=question_id).all()
    return render_template('view_questions.html', question=question, answers=answers)



with app.app_context():
    db.create_all()
    
if __name__ == '__main__':
   
    app.run(debug=True)
