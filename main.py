import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import joblib
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import hashlib
import secrets
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Grievance Portal", layout="wide")

nltk.download('vader_lexicon')
sentiment_analyzer = SentimentIntensityAnalyzer()

# Authentication Class
class Auth:
    def __init__(self):
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect('auth.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS admin_codes (
            code TEXT PRIMARY KEY,
            created_at TIMESTAMP,
            used BOOLEAN DEFAULT FALSE
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            email TEXT,
            full_name TEXT,
            department TEXT,
            verified BOOLEAN DEFAULT FALSE
        )''')
        conn.commit()
        conn.close()

    def generate_admin_code(self):
        code = secrets.token_hex(6)
        conn = sqlite3.connect('auth.db')
        c = conn.cursor()
        c.execute('INSERT INTO admin_codes (code, created_at) VALUES (?, ?)',
                 (code, datetime.now()))
        conn.commit()
        conn.close()
        return code

    def verify_admin_code(self, code):
        conn = sqlite3.connect('auth.db')
        c = conn.cursor()
        c.execute('SELECT used FROM admin_codes WHERE code = ?', (code,))
        result = c.fetchone()
        if result and not result[0]:
            c.execute('UPDATE admin_codes SET used = TRUE WHERE code = ?', (code,))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False

    def register_user(self, data, is_admin=False):
        hashed_pwd = hashlib.sha256(data['password'].encode()).hexdigest()
        conn = sqlite3.connect('auth.db')
        c = conn.cursor()
        
        role = "admin" if is_admin else "user"
        verified = True if is_admin else False
        
        try:
            c.execute('''INSERT INTO users 
                (username, password, role, email, full_name, department, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (data['username'], hashed_pwd, role, data['email'],
                 data['full_name'], data.get('department', ''), verified))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def verify_login(self, username, password):
        hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
        conn = sqlite3.connect('auth.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                 (username, hashed_pwd))
        user = c.fetchone()
        conn.close()
        return user

# Complaint System Class
class ComplaintSystem:
    def __init__(self):
        self.init_db()
        
    def init_db(self):
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                complaint_text TEXT,
                category TEXT,
                severity INTEGER,
                sentiment_score REAL,
                status TEXT,
                created_at TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add_complaint(self, customer_id, complaint_text, category, severity, sentiment_score):
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO complaints 
            (customer_id, complaint_text, category, severity, sentiment_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, complaint_text, category, severity, sentiment_score, 'OPEN', datetime.now()))
        conn.commit()
        conn.close()

    def get_all_complaints(self):
        conn = sqlite3.connect('complaints.db')
        df = pd.read_sql_query('SELECT * FROM complaints', conn)
        conn.close()
        return df

    def update_complaint_status(self, complaint_id, new_status):
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        if new_status == 'RESOLVED':
            c.execute('UPDATE complaints SET status = ?, resolved_at = ? WHERE id = ?', 
                     (new_status, datetime.now(), complaint_id))
        else:
            c.execute('UPDATE complaints SET status = ? WHERE id = ?', 
                     (new_status, complaint_id))
        conn.commit()
        conn.close()

# Pages and Features

def landing_page():
    st.title("Welcome to the Grievance Portal")
    st.write("""The Grievance Portal is designed to help you file complaints, 
    track their progress, and provide feedback efficiently. Whether you are 
    a user or an admin, the portal provides tools for effective communication 
    and resolution management. Explore the following features:

    - **User Registration**: Create your account and access the system.
    - **File Complaints**: Submit complaints with relevant details.
    - **Track Complaints**: Monitor the status and updates on your complaints.
    - **View Dashboard**: Analyze complaint trends and key metrics.

    Use the navigation menu above to get started.""")

# def registration_page():
#     selected_tab = st.tabs(["User Registration", "Admin Registration"])

#     with selected_tab[0]:
#         st.header("User Registration")
#         ufull_name = st.text_input("Full Name*")
#         uemail = st.text_input("Email*")
#         uusername = st.text_input("Username*")
#         upassword = st.text_input("Password*", type="password")
#         if st.button("Register"):
#             if all([ufull_name, uemail, uusername, upassword]):
#                 auth = Auth()
#                 success = auth.register_user({
#                     'username': uusername,
#                     'password': upassword,
#                     'email': uemail,
#                     'full_name': ufull_name
#                 })
#                 if success:
#                     st.success("Registration successful! Please wait for verification.")
#                 else:
#                     st.error("Username already exists")
#             else:
#                 st.error("Required fields cannot be empty")

#     with selected_tab[1]:
#         st.header("Admin Registration")
#         admin_code = st.text_input("Admin Registration Code*")
#         full_name = st.text_input("Name of the Organisation*")
#         email = st.text_input("Official Email*")
#         ausername = st.text_input("Organisation username*")
#         apassword = st.text_input("Admin Password*", type="password")
#         department = st.selectbox("Department*", [
#             "Education", "Healthcare", "Municipal", "Transport", 
#             "Law Enforcement", "Public Works"
#         ])
#         if st.button("Register Admin"):
#             if all([admin_code, full_name, email, ausername, apassword, department]):
#                 auth = Auth()
#                 if auth.verify_admin_code(admin_code):
#                     success = auth.register_user({
#                         'username': ausername,
#                         'password': apassword,
#                         'email': email,
#                         'full_name': full_name,
#                         'department': department
#                     }, is_admin=True)
#                     if success:
#                         st.success("Admin registration successful!")
#                     else:
#                         st.error("Username already exists")
#                 else:
#                     st.error("Invalid or used admin code")
#             else:
#                 st.error("All fields are required")

def complaint_form():
    st.title("File a Complaint")
    customer_id = st.text_input("Customer ID*")
    complaint_text = st.text_area("Complaint Description*")
    category = st.selectbox("Category", ["Service", "Product", "Delivery", "Other"])
    if st.button("Submit Complaint"):
        if all([customer_id, complaint_text, category]):
            sentiment_scores = sentiment_analyzer.polarity_scores(complaint_text)
            sentiment_score = sentiment_scores['compound']
            severity = max(1, min(5, int(abs(sentiment_score * 2.5) + 3)))
            system = ComplaintSystem()
            system.add_complaint(customer_id, complaint_text, category, severity, sentiment_score)
            st.success("Complaint submitted successfully!")
        else:
            st.error("All fields are required")

def view_complaints():
    st.title("View Complaints")
    system = ComplaintSystem()
    df = system.get_all_complaints()
    if not df.empty:
        st.dataframe(df)
        complaint_id = st.number_input("Complaint ID", min_value=1)
        new_status = st.selectbox("New Status", ["OPEN", "IN_PROGRESS", "RESOLVED"])
        if st.button("Update Status"):
            system.update_complaint_status(complaint_id, new_status)
            st.success("Status updated successfully!")
            st.experimental_rerun()
    else:
        st.write("No complaints found.")

def dashboard():
    st.title("Complaints Dashboard")
    system = ComplaintSystem()
    df = system.get_all_complaints()
    if not df.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig_severity = px.histogram(df, x="severity", title="Complaint Severity Distribution")
            st.plotly_chart(fig_severity)

            fig_status = px.pie(df, names="status", title="Complaint Status Distribution")
            st.plotly_chart(fig_status)

        with col2:
            fig_category = px.bar(df['category'].value_counts(), title="Complaint Categories")
            st.plotly_chart(fig_category)

            fig_sentiment = px.line(df.sort_values('created_at'), x='created_at', y='sentiment_score', title="Sentiment Score Trends")
            st.plotly_chart(fig_sentiment)

        st.subheader("Key Metrics")
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

        with metrics_col1:
            st.metric("Total Complaints", len(df))
        with metrics_col2:
            st.metric("Avg Severity", round(df['severity'].mean(), 2))
        with metrics_col3:
            st.metric("Resolution Rate", f"{(df['status'] == 'RESOLVED').mean():.1%}")
        with metrics_col4:
            st.metric("Avg Sentiment", round(df['sentiment_score'].mean(), 2))


menu = option_menu(
    menu_title=None,
    options=["Home", "File Complaint", "View Complaints", "Dashboard"],
    icons=["house", "person-plus", "file-earmark", "table", "bar-chart"],
    default_index=0,
    orientation="horizontal"
)

if menu == "Home":
    landing_page()
elif menu == "File Complaint":
    complaint_form()
elif menu == "View Complaints":
    view_complaints()
elif menu == "Dashboard":
    dashboard()
