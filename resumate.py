import base64
import sqlite3

import pdfplumber
import streamlit as st
import pickle
import re
import nltk
import spacy
import io
import pandas as pd
from pyresparser.utils import extract_experience

# Initialize session state
if "session_state" not in st.session_state:
    st.session_state.session_state = {"logged_in": False}


nltk.download('punkt')
nltk.download('stopwords')

# Load the spaCy English model
nlp = spacy.load('en_core_web_sm')

# Loading models
clf = pickle.load(open('clf.pkl', 'rb'))
tfidfd = pickle.load(open('tfidf.pkl', 'rb'))


def clean_resume(resume_text):
    clean_text = re.sub('http\S+\s*', ' ', resume_text)
    clean_text = re.sub('RT|cc', ' ', clean_text)
    clean_text = re.sub('@\S+', ' ', clean_text)
    clean_text = re.sub('#\S+', ' ', clean_text)
    clean_text = re.sub('[%s]' % re.escape("""!#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""), ' ', clean_text)
    clean_text = re.sub('r[^\x00-\x7f]', ' ', clean_text)
    clean_text = re.sub('â¢', '', clean_text)
    clean_text = re.sub('â', '', clean_text)
    clean_text = re.sub('\s+', ' ', clean_text)  # to remove sequence

    return clean_text



def extract_name_from_resume(resume_text):
    name = None

    # Tokenize the resume text into sentences
    sentences = nltk.sent_tokenize(resume_text)

    # Iterate over each sentence to find a potential name
    for sentence in sentences:
        words = nltk.word_tokenize(sentence)
        # Assuming the name consists of the first two capitalized words in a sentence
        if len(words) >= 2 and words[0].istitle() and words[1].istitle():
            name = ' '.join(words[:2])
            break

    return name

def extract_contact_number_from_resume(resume_text):
    contact_number = None

    # Use regex pattern to find a potential contact number
    pattern = r'\b\d{10}\b'
    match = re.search(pattern, resume_text)
    if match:
        contact_number = match.group()

    return contact_number


def extract_skills(resume_text):
    # List of skill keywords and phrases
    skill_keywords = ['python', 'machine learning', 'data analysis', 'sql', 'java', 'data visualization', 'aws', 'ai', 'regression',
                      'spark', 'sas', 'html', 'css', 'canva', 'php', 'android programming', 'ios programming', 'c', 'javascript',
                      'matlab', 'swift', 'objective-c', 'wordpress', 'data mining', 'latex', 'git', 'photoshop' ]

    # Set to store extracted skills (to remove duplicates)
    skills = set()

    # Tokenize the resume text into individual words
    words = resume_text.lower().split()

    # Check for skill keywords and phrases in the resume text
    for i in range(len(words)):
        for n in range(1, min(4, len(words) - i + 1)):
            phrase = ' '.join(words[i:i+n])
            if phrase in skill_keywords:
                skills.add(phrase)

    return list(skills)


# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            text += page_text + "\n"  # Separate text from different pages
    return text


# web app
def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)



def format_extracted_results(name, contact_number, category_name, extracted_skills, skills_score):
    data = {
        "Name": [name],
        "Contact Number": [contact_number],
        "Category": [category_name],
        "Skills": [", ".join(extracted_skills)],
        "Skills Score": [skills_score],
    }
    df = pd.DataFrame(data)
    return df

def download_extracted_data(dataframe):
    csv = dataframe.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    button_text = "Download Extracted Result"
    href = f'<div style="display: flex; justify-content: center;"><a href="data:file/csv;base64,{b64}" download="extracted_data.csv"><button style="background-color: #3cce59; color: #ffffff; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold; cursor: pointer;">{button_text}</button></a></div>'
    return href

# Function to extract experience information from resume text
def extract_experience(resume_text):
    experience_section = re.search(r'Experience\s*.*', resume_text, re.IGNORECASE)
    if experience_section:
        experience_text = experience_section.group(0)
        experience_lines = experience_text.split('\n')
        experience_lines = [line.strip() for line in experience_lines if line.strip()]
        return experience_lines
    return []


def score_skills(skills):
    # Define a scoring mechanism for skills

    num_skills = len(skills)
    if num_skills >= 5:
        return 5  # High score
    elif num_skills >= 3:
        return 3  # Medium score
    else:
        return 1  # Low score

def calculate_overall_score( skills_score):
    overall_score = (skills_score)
    return overall_score






# Create a database connection
conn = sqlite3.connect('user_data.db')
cursor = conn.cursor()


# Create the "users" table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL
    )
''')
conn.commit()

# Function to handle user registration
def register_user(username, email, password):
    cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
    conn.commit()
    st.success("Registration successful! You can now log in.")


def login_user(email, password):
    # Retrieve the user with the provided username from the database
    cursor.execute("SELECT email, password FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if user:
        stored_password = user[1]  # Password stored in the database
        if stored_password == password:
            return True  # Successful login
        else:
            return False  # Incorrect password
    else:
        return False  # User not found


def registration_form():
    st.title("User Registration")

    new_username = st.text_input("New Username")
    new_email = st.text_input("Email")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        # Validate input and register user
        if new_username and new_email and new_password and confirm_password:
            if new_password == confirm_password:
            # You can add more validation here
                register_user(new_username, new_password)
            else:
                st.warning("Password and confirm password do not match.")
        else:
            st.warning("Please provide all required information.")


def main_web_app():
    # existing web app code

    st.markdown(
        '<p style="font-size: 20px; margin-top: 20px; margin-bottom: -40px; font-weight:bold;">Upload Resume Here</p>',
        unsafe_allow_html=True)
    uploaded_file = st.file_uploader('', type=['txt', 'pdf'])

    # ... (the rest of your existing code for the main content)

    if uploaded_file is not None:
        # Add horizontal line
        st.markdown("<hr style='border-width: 2px;'>", unsafe_allow_html=True)

        save_image_path = './uploaded_resumes/' + uploaded_file.name
        with open(save_image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Display PDF resume

        if uploaded_file.type == "application/pdf":
            resume_text = extract_text_from_pdf(save_image_path)
            show_pdf(save_image_path)
        # Display text resume
        elif uploaded_file.type == "text/plain":
            resume_text = uploaded_file.read().decode('utf-8')
            st.text(resume_text)

        # Add horizontal line
        st.markdown("<hr style='border-width: 2px;'>", unsafe_allow_html=True)

        # topic
        st.write("<h3>After analyzing the resume we found these details!</h3>", unsafe_allow_html=True)

        # Extract name
        name = extract_name_from_resume(resume_text)
        st.write(f"<p style='font-size: 20px; margin-top: 10px;'><b>Name: {name}</b></p>", unsafe_allow_html=True)

        cleaned_resume = clean_resume(resume_text)
        extracted_skills = extract_skills(cleaned_resume)
        input_features = tfidfd.transform([cleaned_resume])

        # Extract contact number
        contact_number = extract_contact_number_from_resume(resume_text)
        st.write(f"<p style='font-size: 20px; margin-top: -10px;'><b>Contact Number: {contact_number}</b></p>",
                 unsafe_allow_html=True)

        # Map category ID to category name
        category_mapping = {
            15: "Java Developer",
            23: "Testing",
            8: "DevOps Engineer",
            20: "Python Developer",
            24: "Web Designing",
            12: "HR",
            13: "Hadoop",
            3: "Blockchain",
            10: "ETL Developer",
            18: "Operations Manager",
            6: "Data Science",
            22: "Sales",
            16: "Mechanical Engineering",
            1: "Arts",
            7: "Database",
            11: "Electrical Engineering",
            14: "Health and fitness",
            19: "PMO",
            4: "Business Analyst",
            9: "Dotnet Developer",
            2: "Automatic Testing",
            17: "Network Security Engineer",
            21: "SAP Developer",
            5: "Civil Engineer",
            0: "Advocate",
        }

        prediction_id = clf.predict(input_features)[0]

        # category_name = category_mapping.get(prediction_id, "Unknown")

        # Map category ID to category name
        category_name = category_mapping.get(prediction_id, "Unknown")
        st.write(f"<p style='font-size: 20px; margin-top: -10px;'><b>Predicted category: {category_name}</b></p>",
                 unsafe_allow_html=True)

        # Extracted skills
        extracted_skills = extract_skills(cleaned_resume)
        skills_text = "\n".join([f"{i}: {skill}" for i, skill in enumerate(extracted_skills)])
        st.write(f"<p style='font-size:20px; margin-top: -10px; margin-bottom: -28px;'><b>Extracted skills:</b>",
                 unsafe_allow_html=True)
        st.code(f"{skills_text}", language="python")

        # Extract experience
        extracted_experience = extract_experience(resume_text)
        if extracted_experience:
            st.write("<p style='font-size: 20px; margin-top: -10px;'><b>Extracted Experience:</b></p>",
                     unsafe_allow_html=True)
            for exp_line in extracted_experience:
                st.write(exp_line)
        else:
            st.write("<p>No experience information found.</p>", unsafe_allow_html=True)

            # Calculate skills score
        skills_score = score_skills(extracted_skills)

        # Display the scores
        st.write(f"<p style='font-size: 20px; margin-top: 10px;'><b>Skills Score: {skills_score}</b></p>",
                 unsafe_allow_html=True)

        # Add horizontal line
        st.markdown("<hr style='border-width: 2px;'>", unsafe_allow_html=True)

        # Format extracted results as DataFrame
        extracted_data = format_extracted_results(name, contact_number, category_name, extracted_skills,
                                                  skills_score)
        st.write(
            f"<p style='font-size:25px; margin-top: 20px;'><b>Download the result in CSV format from here!</b></p>",
            unsafe_allow_html=True)
        st.dataframe(extracted_data)

        # Download extracted data as CSV
        download_link = download_extracted_data(extracted_data)
        st.markdown(download_link, unsafe_allow_html=True)

        # Add horizontal line
        st.markdown("<hr style='border-width: 2px;'>", unsafe_allow_html=True)

        # Logout button
        if st.button("Logout"):
            st.session_state.logged_in = False


# Custom SessionState class
class SessionState:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def main():
    # st.set_page_config(page_title="Resumate: Resume Analyzer", page_icon="📄")

    if st.session_state.logged_in:
        main_web_app()

    else:
        st.title("Resumate: Resume Analyzer")
        user_action = st.sidebar.radio("Select Action", ["Login", "Register"])

        if user_action == "Register":
            st.sidebar.header("User Registration")
            new_username = st.sidebar.text_input("New Username")
            new_email = st.sidebar.text_input("Email")
            new_password = st.sidebar.text_input("New Password", type="password")
            confirm_password = st.sidebar.text_input("Confirm Password", type="password")


            if st.sidebar.button("Register"):
                # Validate input and register user
                if new_username and new_email and new_password and confirm_password:
                    if new_password == confirm_password:
                        # validation here
                        register_user(new_username, new_email, new_password)
                    else:
                        st.warning("Password and confirm password do not match.")
                else:
                    st.warning("Please provide all required information.")

        elif user_action == "Login":
            st.sidebar.header("User Login")
            email = st.sidebar.text_input("Email")
            password = st.sidebar.text_input("Password", type="password")

            if st.sidebar.button("Login"):
                # Login the user and redirect to the main web app
                if login_user(email, password):
                    st.session_state.logged_in = True
                    main_web_app()
                    return
                else:
                    st.warning("Invalid Credentials! Please register if you have not yet!!!")



if __name__ == "__main__":
    if "logged_in" not in st.session_state:  # Initialize the logged_in attribute
        st.session_state.logged_in = False
    main()

