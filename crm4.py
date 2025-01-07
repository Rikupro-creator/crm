import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import sqlite3
import hashlib
from pathlib import Path
import icalendar
from datetime import datetime, timedelta
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import json
import hashlib
import base64
from pathlib import Path


# Initialize database
def init_db():
    conn = sqlite3.connect('crm.db', check_same_thread=False)
    c = conn.cursor()
    
    # Create customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE,
                  phone TEXT,
                  company TEXT,
                  status TEXT,
                  created_date TIMESTAMP)''')
    
    # Create contacts table
    c.execute('''CREATE TABLE IF NOT EXISTS contacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_id INTEGER,
                  type TEXT,
                  notes TEXT,
                  date TIMESTAMP,
                  FOREIGN KEY (customer_id) REFERENCES customers(id))''')
    
    # Create deals table
    c.execute('''CREATE TABLE IF NOT EXISTS deals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_id INTEGER,
                  title TEXT,
                  amount REAL,
                  stage TEXT,
                  probability INTEGER,
                  expected_close TIMESTAMP,
                  FOREIGN KEY (customer_id) REFERENCES customers(id))''')
    
    # Create tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_id INTEGER,
                  title TEXT,
                  description TEXT,
                  due_date TIMESTAMP,
                  status TEXT,
                  FOREIGN KEY (customer_id) REFERENCES customers(id))''')
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS landing_pages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  content TEXT,
                  template TEXT,
                  meta_description TEXT,
                  published BOOLEAN,
                  visits INTEGER DEFAULT 0)''')
    
    # Blog posts
    c.execute('''CREATE TABLE IF NOT EXISTS blog_posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  content TEXT,
                  author_id INTEGER,
                  categories TEXT,
                  tags TEXT,
                  status TEXT,
                  published_date TIMESTAMP)''')
    
    # Marketing campaigns
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  type TEXT,
                  start_date TIMESTAMP,
                  end_date TIMESTAMP,
                  budget REAL,
                  status TEXT,
                  target_audience TEXT)''')
    
    # Forms
    c.execute('''CREATE TABLE IF NOT EXISTS forms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  fields TEXT,
                  submission_count INTEGER DEFAULT 0,
                  thank_you_message TEXT)''')
    
    # Keywords
    c.execute('''CREATE TABLE IF NOT EXISTS keywords
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  keyword TEXT,
                  difficulty INTEGER,
                  volume INTEGER,
                  ranking INTEGER)''')
    
    # Workflow automation
    c.execute('''CREATE TABLE IF NOT EXISTS workflows
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  trigger_type TEXT,
                  conditions TEXT,
                  actions TEXT,
                  status TEXT)''')
    
    conn.commit()
    return conn

# Authentication functions
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(password, hashed_password):
    return hash_password(password) == hashed_password

def login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("CRM Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            conn = init_db()
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username=?", (username,))
            result = c.fetchone()
            
            if result and check_password(password, result[0]):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid username or password")
        
        if st.button("Register"):
            conn = init_db()
            c = conn.cursor()
            hashed_pw = hash_password(password)
            try:
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                         (username, hashed_pw, 'user'))
                conn.commit()
                st.success("Registration successful!")
            except sqlite3.IntegrityError:
                st.error("Username already exists!")
        return False
    return True

# [Rest of the code remains exactly the same as before]

# Customer Management
def add_customer():
    st.subheader("Add New Customer")
    with st.form("add_customer_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        company = st.text_input("Company")
        status = st.selectbox("Status", ["Lead", "Customer", "Inactive"])
        
        if st.form_submit_button("Add Customer"):
            conn = init_db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO customers (name, email, phone, company, status, created_date)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                         (name, email, phone, company, status, datetime.now()))
                conn.commit()
                st.success("Customer added successfully!")
            except sqlite3.IntegrityError:
                st.error("Email already exists!")

def view_customers():
    st.subheader("Customer List")
    conn = init_db()
    df = pd.read_sql_query("SELECT * FROM customers", conn)
    
    # Filters
    status_filter = st.multiselect("Filter by Status", df['status'].unique())
    if status_filter:
        df = df[df['status'].isin(status_filter)]
    
    # Search
    search = st.text_input("Search customers")
    if search:
        df = df[df['name'].str.contains(search, case=False) | 
                df['email'].str.contains(search, case=False)]
    
    st.dataframe(df)
    
    # Customer details
    if st.button("View Customer Details"):
        customer_id = st.number_input("Enter Customer ID", min_value=1)
        show_customer_details(customer_id)

# Deal Management
def manage_deals():
    st.subheader("Deal Management")
    
    # Add new deal
    with st.form("add_deal_form"):
        customer_id = st.number_input("Customer ID", min_value=1)
        title = st.text_input("Deal Title")
        amount = st.number_input("Amount", min_value=0.0)
        stage = st.selectbox("Stage", ["Prospecting", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"])
        probability = st.slider("Probability (%)", 0, 100)
        expected_close = st.date_input("Expected Close Date")
        
        if st.form_submit_button("Add Deal"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO deals (customer_id, title, amount, stage, probability, expected_close)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (customer_id, title, amount, stage, probability, expected_close))
            conn.commit()
            st.success("Deal added successfully!")
    
    # View deals
    conn = init_db()
    deals_df = pd.read_sql_query("""
        SELECT deals.*, customers.name as customer_name 
        FROM deals 
        JOIN customers ON deals.customer_id = customers.id
    """, conn)
    
    # Deal pipeline visualization
    fig = px.bar(deals_df, x="stage", y="amount", color="probability",
                 title="Deal Pipeline", hover_data=["title", "customer_name"])
    st.plotly_chart(fig)
    
    st.dataframe(deals_df)

# Task Management
def manage_tasks():
    st.subheader("Task Management")
    
    # Add new task
    with st.form("add_task_form"):
        customer_id = st.number_input("Customer ID", min_value=1)
        title = st.text_input("Task Title")
        description = st.text_area("Description")
        due_date = st.date_input("Due Date")
        status = st.selectbox("Status", ["Not Started", "In Progress", "Completed", "Delayed"])
        
        if st.form_submit_button("Add Task"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO tasks (customer_id, title, description, due_date, status)
                        VALUES (?, ?, ?, ?, ?)""",
                     (customer_id, title, description, due_date, status))
            conn.commit()
            st.success("Task added successfully!")
    
    # View tasks
    conn = init_db()
    tasks_df = pd.read_sql_query("""
        SELECT tasks.*, customers.name as customer_name 
        FROM tasks 
        JOIN customers ON tasks.customer_id = customers.id
    """, conn)
    
    # Task filters
    status_filter = st.multiselect("Filter by Status", tasks_df['status'].unique())
    if status_filter:
        tasks_df = tasks_df[tasks_df['status'].isin(status_filter)]
    
    st.dataframe(tasks_df)

# Contact Management
def manage_contacts():
    st.subheader("Contact Management")
    
    # Add new contact record
    with st.form("add_contact_form"):
        customer_id = st.number_input("Customer ID", min_value=1)
        contact_type = st.selectbox("Contact Type", ["Email", "Phone", "Meeting", "Note"])
        notes = st.text_area("Notes")
        
        if st.form_submit_button("Add Contact Record"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO contacts (customer_id, type, notes, date)
                        VALUES (?, ?, ?, ?)""",
                     (customer_id, contact_type, notes, datetime.now()))
            conn.commit()
            st.success("Contact record added successfully!")
    
    # View contact history
    conn = init_db()
    contacts_df = pd.read_sql_query("""
        SELECT contacts.*, customers.name as customer_name 
        FROM contacts 
        JOIN customers ON contacts.customer_id = customers.id
        ORDER BY date DESC
    """, conn)
    
    st.dataframe(contacts_df)

# Dashboard
def show_dashboard():
    st.title("CRM Dashboard")
    
    conn = init_db()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Total customers
    total_customers = pd.read_sql_query("""
        SELECT COUNT(*) as count FROM customers
    """, conn).iloc[0]['count']
    col1.metric("Total Customers", total_customers)
    
    # Total deals and pipeline value
    deals_data = pd.read_sql_query("""
        SELECT COUNT(*) as count, 
               COALESCE(SUM(amount), 0) as total_amount 
        FROM deals 
        WHERE stage != 'Closed Lost'
    """, conn)
    
    active_deals = deals_data.iloc[0]['count']
    pipeline_value = deals_data.iloc[0]['total_amount']
    
    col2.metric("Active Deals", active_deals)
    col3.metric("Pipeline Value", f"${pipeline_value:,.2f}")
    
    # Tasks due today
    tasks_due = pd.read_sql_query("""
        SELECT COUNT(*) as count 
        FROM tasks 
        WHERE date(due_date) = date('now') 
        AND status != 'Completed'
    """, conn).iloc[0]['count']
    col4.metric("Tasks Due Today", tasks_due)
    
    # Deal pipeline chart
    deals_df = pd.read_sql_query("""
        SELECT stage, 
               COUNT(*) as count, 
               COALESCE(SUM(amount), 0) as total_amount
        FROM deals 
        GROUP BY stage
    """, conn)
    
    if not deals_df.empty:
        fig1 = px.bar(deals_df, x="stage", y="total_amount",
                      title="Deal Pipeline by Stage")
        st.plotly_chart(fig1)
    else:
        st.info("No deals data available for visualization")
    
    # Recent activities
    st.subheader("Recent Activities")
    activities_df = pd.read_sql_query("""
        SELECT contacts.date, 
               customers.name as customer_name, 
               contacts.type, 
               contacts.notes
        FROM contacts 
        JOIN customers ON contacts.customer_id = customers.id
        ORDER BY contacts.date DESC 
        LIMIT 10
    """, conn)
    
    if not activities_df.empty:
        st.dataframe(activities_df)
    else:
        st.info("No recent activities to display")
def update_enhanced_schema():
    conn = init_db()
    c = conn.cursor()
    
    # Internal messaging system
    c.execute('''CREATE TABLE IF NOT EXISTS internal_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_id INTEGER,
                  receiver_id INTEGER,
                  message TEXT,
                  sent_date TIMESTAMP,
                  read_status BOOLEAN)''')
    
    # Meeting notes and follow-ups
    c.execute('''CREATE TABLE IF NOT EXISTS meeting_notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_id INTEGER,
                  meeting_date TIMESTAMP,
                  attendees TEXT,
                  notes TEXT,
                  action_items TEXT,
                  follow_up_date TIMESTAMP)''')
    
    # Customer preferences
    c.execute('''CREATE TABLE IF NOT EXISTS customer_preferences
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_id INTEGER,
                  preferred_contact_method TEXT,
                  preferred_meeting_time TEXT,
                  interests TEXT,
                  birthday DATE)''')
    
    # Sales forecasting
    c.execute('''CREATE TABLE IF NOT EXISTS sales_forecasts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  period TEXT,
                  predicted_revenue REAL,
                  confidence_level INTEGER,
                  notes TEXT)''')

    # Performance metrics
    c.execute('''CREATE TABLE IF NOT EXISTS performance_metrics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  metric_type TEXT,
                  value REAL,
                  date TIMESTAMP)''')

    conn.commit()
    return conn

def team_collaboration():
    st.subheader("Team Collaboration")
    
    with st.form("internal_message"):
        receiver = st.selectbox("To", pd.read_sql_query("SELECT username FROM users", init_db())['username'])
        message = st.text_area("Message")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        
        if st.form_submit_button("Send Message"):
            conn = init_db()
            c = conn.cursor()
            c.execute("INSERT INTO internal_messages (sender_id, receiver_id, message, sent_date, read_status) VALUES (?, ?, ?, ?, ?)",
                     (st.session_state.user_id, receiver, message, datetime.now(), False))
            conn.commit()

def meeting_management():
    st.subheader("Meeting Management")
    
    with st.form("meeting_notes"):
        customer = st.selectbox("Customer", pd.read_sql_query("SELECT name FROM customers", init_db())['name'])
        meeting_date = st.date_input("Meeting Date")
        attendees = st.text_area("Attendees")
        notes = st.text_area("Notes")
        action_items = st.text_area("Action Items")
        follow_up = st.date_input("Follow-up Date")
        
        if st.form_submit_button("Save Meeting Notes"):
            conn = init_db()
            c = conn.cursor()
            c.execute("INSERT INTO meeting_notes VALUES (?, ?, ?, ?, ?, ?)",
                     (customer, meeting_date, attendees, notes, action_items, follow_up))
            conn.commit()

def sales_forecasting():
    st.subheader("Sales Forecasting")
    
    historical_data = pd.read_sql_query("""
        SELECT strftime('%Y-%m', expected_close) as period,
               SUM(amount * probability / 100) as weighted_amount
        FROM deals
        GROUP BY period
        ORDER BY period
    """, init_db())
    
    # Simple moving average forecast
    if not historical_data.empty:
        historical_data['forecast'] = historical_data['weighted_amount'].rolling(window=3).mean()
        
        fig = px.line(historical_data, x='period', y=['weighted_amount', 'forecast'],
                     title='Sales Forecast')
        st.plotly_chart(fig)

def performance_dashboard():
    st.subheader("Performance Metrics")
    
    metrics = pd.read_sql_query("""
        SELECT u.username,
               COUNT(d.id) as deals_closed,
               SUM(d.amount) as revenue_generated,
               AVG(d.probability) as avg_deal_probability
        FROM users u
        LEFT JOIN deals d ON u.id = d.user_id
        GROUP BY u.username
    """, init_db())
    
    st.dataframe(metrics)
    
# Email Management Functions
def manage_email_templates():
    st.subheader("Email Template Management")
    
    # Add new template
    with st.form("new_template"):
        template_name = st.text_input("Template Name")
        subject = st.text_input("Email Subject")
        body = st.text_area("Email Body")
        
        # Template variables helper
        st.info("Available variables: {customer_name}, {company_name}, {deal_value}, {due_date}")
        
        if st.form_submit_button("Save Template"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO email_templates (name, subject, body, created_date)
                        VALUES (?, ?, ?, ?)""",
                     (template_name, subject, body, datetime.now()))
            conn.commit()
            st.success("Template saved successfully!")
    
    # View and edit existing templates
    st.subheader("Existing Templates")
    conn = init_db()
    templates_df = pd.read_sql_query("SELECT * FROM email_templates", conn)
    if not templates_df.empty:
        selected_template = st.selectbox("Select template to edit", templates_df['name'])
        template_data = templates_df[templates_df['name'] == selected_template].iloc[0]
        
        with st.form("edit_template"):
            new_subject = st.text_input("Subject", value=template_data['subject'])
            new_body = st.text_area("Body", value=template_data['body'])
            
            if st.form_submit_button("Update Template"):
                c = conn.cursor()
                c.execute("""UPDATE email_templates 
                           SET subject=?, body=? 
                           WHERE id=?""",
                        (new_subject, new_body, template_data['id']))
                conn.commit()
                st.success("Template updated successfully!")

def send_email(to_email, subject, body):
    # This is a placeholder for email sending functionality
    # In a real application, you would configure your SMTP server
    st.info(f"Email would be sent to: {to_email}\nSubject: {subject}\nBody: {body}")
    return True

def manage_communications():
    st.subheader("Communication Management")
    
    # Select customer
    conn = init_db()
    customers_df = pd.read_sql_query("SELECT id, name, email FROM customers", conn)
    selected_customer = st.selectbox("Select Customer", customers_df['name'])
    customer_data = customers_df[customers_df['name'] == selected_customer].iloc[0]
    
    # Communication options
    comm_type = st.selectbox("Communication Type", ["Email", "Note", "Call Log"])
    
    if comm_type == "Email":
        # Template selection
        templates_df = pd.read_sql_query("SELECT * FROM email_templates", conn)
        if not templates_df.empty:
            selected_template = st.selectbox("Select Template", templates_df['name'])
            template_data = templates_df[templates_df['name'] == selected_template].iloc[0]
            
            # Parse template
            subject = template_data['subject']
            body = template_data['body']
            
            # Replace variables
            subject = subject.replace("{customer_name}", customer_data['name'])
            body = body.replace("{customer_name}", customer_data['name'])
            
            # Allow editing
            final_subject = st.text_input("Subject", value=subject)
            final_body = st.text_area("Body", value=body)
            
            if st.button("Send Email"):
                if send_email(customer_data['email'], final_subject, final_body):
                    # Log communication
                    c = conn.cursor()
                    c.execute("""INSERT INTO communication_logs 
                               (customer_id, type, subject, content, sent_date, status)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                             (customer_data['id'], 'Email', final_subject, 
                              final_body, datetime.now(), 'Sent'))
                    conn.commit()
                    st.success("Email sent and logged successfully!")

# Enhanced Analytics Functions
def show_enhanced_analytics():
    st.subheader("Enhanced Analytics Dashboard")
    
    conn = init_db()
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", 
                                  value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now())
    
    # Sales Performance
    deals_df = pd.read_sql_query(f"""
        SELECT stage, COUNT(*) as count, SUM(amount) as total_amount,
               strftime('%Y-%m', expected_close) as month
        FROM deals
        WHERE date(expected_close) BETWEEN ? AND ?
        GROUP BY stage, month
        ORDER BY month
    """, conn, params=(start_date, end_date))
    
    if not deals_df.empty:
        # Pipeline Progress
        fig1 = px.funnel(deals_df, x='count', y='stage', 
                        title="Deal Pipeline Funnel")
        st.plotly_chart(fig1)
        
        # Monthly Revenue Trend
        fig2 = px.line(deals_df, x='month', y='total_amount', 
                      title="Monthly Revenue Trend",
                      labels={'total_amount': 'Revenue', 'month': 'Month'})
        st.plotly_chart(fig2)
    
    # Customer Acquisition Analysis
    customers_df = pd.read_sql_query(f"""
        SELECT strftime('%Y-%m', created_date) as month,
               COUNT(*) as new_customers,
               status
        FROM customers
        WHERE date(created_date) BETWEEN ? AND ?
        GROUP BY month, status
    """, conn, params=(start_date, end_date))
    
    if not customers_df.empty:
        fig3 = px.bar(customers_df, x='month', y='new_customers', 
                     color='status', title="Customer Acquisition by Status",
                     labels={'new_customers': 'New Customers', 'month': 'Month'})
        st.plotly_chart(fig3)

# Data Management Functions
def manage_custom_fields():
    st.subheader("Custom Fields Management")
    
    # Add new custom field
    with st.form("new_custom_field"):
        entity_type = st.selectbox("Entity Type", ["Customer", "Deal", "Task"])
        field_name = st.text_input("Field Name")
        field_type = st.selectbox("Field Type", ["Text", "Number", "Date", "Dropdown"])
        required = st.checkbox("Required Field")
        
        if st.form_submit_button("Add Custom Field"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO custom_fields 
                        (entity_type, field_name, field_type, required)
                        VALUES (?, ?, ?, ?)""",
                     (entity_type, field_name, field_type, required))
            conn.commit()
            st.success("Custom field added successfully!")

def import_export_data():
    st.subheader("Data Import/Export")
    
    # Export Data
    st.write("### Export Data")
    export_type = st.selectbox("Select data to export", 
                              ["Customers", "Deals", "Tasks", "Communications"])
    
    if st.button("Export to CSV"):
        conn = init_db()
        if export_type == "Customers":
            df = pd.read_sql_query("SELECT * FROM customers", conn)
        elif export_type == "Deals":
            df = pd.read_sql_query("SELECT * FROM deals", conn)
        elif export_type == "Tasks":
            df = pd.read_sql_query("SELECT * FROM tasks", conn)
        else:
            df = pd.read_sql_query("SELECT * FROM communication_logs", conn)
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{export_type.lower()}_export.csv",
            mime="text/csv"
        )
    
    # Import Data
    st.write("### Import Data")
    import_type = st.selectbox("Select data to import", 
                              ["Customers", "Deals", "Tasks"])
    uploaded_file = st.file_uploader("Choose a CSV file")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Preview of data to be imported:")
            st.write(df.head())
            
            if st.button("Confirm Import"):
                conn = init_db()
                table_name = import_type.lower()
                df.to_sql(table_name, conn, if_exists='append', index=False)
                st.success(f"Successfully imported {len(df)} records!")
        except Exception as e:
            st.error(f"Error importing data: {str(e)}")

def update_advanced_schema():
    conn = init_db()
    c = conn.cursor()
    
    # Calendar events
    c.execute('''CREATE TABLE IF NOT EXISTS calendar_events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  description TEXT,
                  start_time TIMESTAMP,
                  end_time TIMESTAMP,
                  customer_id INTEGER,
                  event_type TEXT,
                  location TEXT,
                  attendees TEXT,
                  FOREIGN KEY (customer_id) REFERENCES customers(id))''')
    
    # Document storage
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  type TEXT,
                  content BLOB,
                  customer_id INTEGER,
                  upload_date TIMESTAMP,
                  tags TEXT,
                  FOREIGN KEY (customer_id) REFERENCES customers(id))''')
    
    # Automation rules
    c.execute('''CREATE TABLE IF NOT EXISTS automation_rules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  trigger_type TEXT,
                  trigger_conditions TEXT,
                  action_type TEXT,
                  action_details TEXT,
                  is_active BOOLEAN)''')
    
    # Lead scoring rules
    c.execute('''CREATE TABLE IF NOT EXISTS lead_scoring_rules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  attribute TEXT,
                  condition TEXT,
                  score INTEGER)''')
    
    conn.commit()
    return conn
def content_management():
    st.subheader("Content Management")
    
    tab1, tab2 = st.tabs(["Landing Pages", "Blog Posts"])
    
    with tab1:
        with st.form("landing_page"):
            title = st.text_input("Page Title")
            template = st.selectbox("Template", ["Default", "Product", "Event", "Thank You"])
            content = st.text_area("Content", height=300)
            meta_description = st.text_input("Meta Description")
            
            if st.form_submit_button("Save Page"):
                conn = init_db()
                c = conn.cursor()
                c.execute("""INSERT INTO landing_pages 
                           (title, content, template, meta_description, published)
                           VALUES (?, ?, ?, ?, ?)""",
                         (title, content, template, meta_description, False))
                conn.commit()
    
    with tab2:
        with st.form("blog_post"):
            post_title = st.text_input("Post Title")
            categories = st.multiselect("Categories", ["Marketing", "Sales", "Technology", "Industry News"])
            tags = st.text_input("Tags (comma-separated)")
            post_content = st.text_area("Content", height=300)
            
            if st.form_submit_button("Save Post"):
                conn = init_db()
                c = conn.cursor()
                c.execute("""INSERT INTO blog_posts 
                           (title, content, author_id, categories, tags, status)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                         (post_title, post_content, st.session_state.user_id, 
                          ','.join(categories), tags, 'draft'))
                conn.commit()

def marketing_campaigns():
    st.subheader("Marketing Campaigns")
    
    with st.form("campaign"):
        name = st.text_input("Campaign Name")
        campaign_type = st.selectbox("Type", ["Email", "Social", "Event", "Webinar"])
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        budget = st.number_input("Budget", min_value=0.0)
        target = st.text_area("Target Audience")
        
        if st.form_submit_button("Create Campaign"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO campaigns 
                       (name, type, start_date, end_date, budget, status, target_audience)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (name, campaign_type, start_date, end_date, budget, 'draft', target))
            conn.commit()

def form_builder():
    st.subheader("Form Builder")
    
    with st.form("create_form"):
        form_name = st.text_input("Form Name")
        fields = []
        num_fields = st.number_input("Number of Fields", min_value=1, max_value=10)
        
        for i in range(int(num_fields)):
            col1, col2 = st.columns(2)
            with col1:
                field_name = st.text_input(f"Field {i+1} Name")
            with col2:
                field_type = st.selectbox(f"Field {i+1} Type", 
                    ["Text", "Email", "Phone", "Number", "Dropdown"], key=f"field_{i}")
            fields.append({"name": field_name, "type": field_type})
        
        thank_you = st.text_area("Thank You Message")
        
        if st.form_submit_button("Create Form"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO forms (name, fields, thank_you_message)
                        VALUES (?, ?, ?)""",
                     (form_name, json.dumps(fields), thank_you))
            conn.commit()

def seo_tools():
    st.subheader("SEO Tools")
    
    tab1, tab2 = st.tabs(["Keyword Tracking", "Content Performance"])
    
    with tab1:
        with st.form("add_keyword"):
            keyword = st.text_input("Keyword")
            difficulty = st.slider("Difficulty", 1, 100)
            volume = st.number_input("Search Volume", min_value=0)
            ranking = st.number_input("Current Ranking", min_value=0)
            
            if st.form_submit_button("Add Keyword"):
                conn = init_db()
                c = conn.cursor()
                c.execute("""INSERT INTO keywords 
                           (keyword, difficulty, volume, ranking)
                           VALUES (?, ?, ?, ?)""",
                         (keyword, difficulty, volume, ranking))
                conn.commit()
    
    with tab2:
        content_stats = pd.read_sql_query("""
            SELECT title, visits FROM landing_pages
            UNION ALL
            SELECT title, 0 as visits FROM blog_posts
        """, init_db())
        
        if not content_stats.empty:
            fig = px.bar(content_stats, x='title', y='visits',
                        title='Content Performance')
            st.plotly_chart(fig)

def workflow_automation():
    st.subheader("Workflow Automation")
    
    with st.form("create_workflow"):
        name = st.text_input("Workflow Name")
        trigger = st.selectbox("Trigger", ["Form Submission", "Page Visit", "Deal Stage Change"])
        
        st.write("Conditions")
        col1, col2 = st.columns(2)
        with col1:
            field = st.selectbox("Field", ["Email", "Company Size", "Industry"])
        with col2:
            operator = st.selectbox("Operator", ["Equals", "Contains", "Greater Than"])
        value = st.text_input("Value")
        
        st.write("Actions")
        actions = st.multiselect("Select Actions", 
            ["Send Email", "Create Task", "Update Property", "Create Deal"])
        
        if st.form_submit_button("Create Workflow"):
            conn = init_db()
            c = conn.cursor()
            workflow_data = {
                "conditions": {"field": field, "operator": operator, "value": value},
                "actions": actions
            }
            c.execute("""INSERT INTO workflows (name, trigger_type, conditions, actions, status)
                        VALUES (?, ?, ?, ?, ?)""",
                     (name, trigger, json.dumps(workflow_data["conditions"]), 
                      json.dumps(workflow_data["actions"]), "active"))
            conn.commit()
            
def calendar_management():
    st.subheader("Calendar Management")
    
    # Add event
    with st.form("add_event"):
        title = st.text_input("Event Title")
        description = st.text_area("Description")
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.datetime_input("Start Time")
        with col2:
            end_time = st.datetime_input("End Time")
        
        customer_id = st.selectbox("Related Customer", 
            pd.read_sql_query("SELECT id, name FROM customers", init_db())['name'])
        event_type = st.selectbox("Event Type", 
            ["Meeting", "Call", "Follow-up", "Presentation"])
        location = st.text_input("Location")
        attendees = st.text_area("Attendees (one email per line)")
        
        if st.form_submit_button("Schedule Event"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO calendar_events
                        (title, description, start_time, end_time, 
                         customer_id, event_type, location, attendees)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     (title, description, start_time, end_time,
                      customer_id, event_type, location, attendees))
            conn.commit()
            
            # Create iCal event
            event = icalendar.Event()
            event.add('summary', title)
            event.add('description', description)
            event.add('dtstart', start_time)
            event.add('dtend', end_time)
            event.add('location', location)
            
            # Generate iCal file
            cal = icalendar.Calendar()
            cal.add_component(event)
            
            # Offer download
            st.download_button(
                "Download iCal File",
                cal.to_ical(),
                file_name="event.ics",
                mime="text/calendar"
            )

def document_management():
    st.subheader("Document Management")
    
    # Upload document
    uploaded_file = st.file_uploader("Upload Document", 
        type=['pdf', 'doc', 'docx', 'txt'])
    if uploaded_file:
        name = uploaded_file.name
        content = uploaded_file.read()
        customer_id = st.selectbox("Related Customer",
            pd.read_sql_query("SELECT id, name FROM customers", init_db())['name'])
        tags = st.text_input("Tags (comma-separated)")
        
        if st.button("Save Document"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO documents
                        (name, type, content, customer_id, upload_date, tags)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (name, uploaded_file.type, content, 
                      customer_id, datetime.now(), tags))
            conn.commit()
            st.success("Document uploaded successfully!")

def automation_rules():
    st.subheader("Automation Rules")
    
    # Add automation rule
    with st.form("add_automation"):
        name = st.text_input("Rule Name")
        trigger_type = st.selectbox("Trigger", 
            ["New Lead", "Deal Stage Change", "Task Due", "Score Change"])
        
        # Dynamic conditions based on trigger
        if trigger_type == "New Lead":
            conditions = {
                "lead_source": st.selectbox("Lead Source",
                    ["Website", "Referral", "Social Media"]),
                "minimum_score": st.number_input("Minimum Score", min_value=0)
            }
        elif trigger_type == "Deal Stage Change":
            conditions = {
                "from_stage": st.selectbox("From Stage",
                    ["Prospecting", "Qualification", "Proposal"]),
                "to_stage": st.selectbox("To Stage",
                    ["Qualification", "Proposal", "Closed Won"])
            }
        
        action_type = st.selectbox("Action",
            ["Send Email", "Create Task", "Update Field", "Notify Team"])
        
        # Dynamic action details
        if action_type == "Send Email":
            action_details = {
                "template_id": st.selectbox("Email Template",
                    pd.read_sql_query("SELECT id, name FROM email_templates", 
                                    init_db())['name']),
                "delay_hours": st.number_input("Delay (hours)", min_value=0)
            }
        elif action_type == "Create Task":
            action_details = {
                "task_title": st.text_input("Task Title"),
                "assignee": st.selectbox("Assignee",
                    ["Sales Rep", "Account Manager", "Support"])
            }
        
        if st.form_submit_button("Create Rule"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO automation_rules
                        (name, trigger_type, trigger_conditions,
                         action_type, action_details, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (name, trigger_type, json.dumps(conditions),
                      action_type, json.dumps(action_details), True))
            conn.commit()
            st.success("Automation rule created!")

def lead_scoring():
    st.subheader("Lead Scoring System")
    
    # Add scoring rule
    with st.form("add_scoring_rule"):
        attribute = st.selectbox("Attribute",
            ["Company Size", "Industry", "Interaction Level", "Budget"])
        condition = st.text_input("Condition (e.g., >100 employees)")
        score = st.number_input("Score Points", min_value=1)
        
        if st.form_submit_button("Add Scoring Rule"):
            conn = init_db()
            c = conn.cursor()
            c.execute("""INSERT INTO lead_scoring_rules
                        (attribute, condition, score)
                        VALUES (?, ?, ?)""",
                     (attribute, condition, score))
            conn.commit()
            st.success("Scoring rule added!")
    
    # Calculate scores for all leads
    if st.button("Calculate Lead Scores"):
        conn = init_db()
        leads_df = pd.read_sql_query("""
            SELECT * FROM customers WHERE status='Lead'
        """, conn)
        
        rules_df = pd.read_sql_query("""
            SELECT * FROM lead_scoring_rules
        """, conn)
        
        # Simple scoring example
        scores = {}
        for _, lead in leads_df.iterrows():
            score = 0
            # Add company size score
            if lead.get('company_size', 0) > 100:
                score += 20
            # Add interaction score
            interactions = pd.read_sql_query("""
                SELECT COUNT(*) as count FROM contacts 
                WHERE customer_id=?
            """, conn, params=(lead['id'],)).iloc[0]['count']
            score += interactions * 5
            
            scores[lead['id']] = score
        
        # Update scores in database
        c = conn.cursor()
        for lead_id, score in scores.items():
            c.execute("""UPDATE customers 
                        SET lead_score=? WHERE id=?""",
                     (score, lead_id))
        conn.commit()
        
        # Show scores
        scored_leads = pd.read_sql_query("""
            SELECT name, lead_score FROM customers 
            WHERE status='Lead' ORDER BY lead_score DESC
        """, conn)
        st.write("Lead Scores:")
        st.dataframe(scored_leads)

def customer_segmentation():
    st.subheader("Customer Segmentation")
    
    conn = init_db()
    customers_df = pd.read_sql_query("""
        SELECT c.*, 
               COUNT(d.id) as total_deals,
               SUM(d.amount) as total_revenue,
               AVG(d.amount) as avg_deal_size
        FROM customers c
        LEFT JOIN deals d ON c.id = d.customer_id
        GROUP BY c.id
    """, conn)
    
    if not customers_df.empty:
        # Prepare data for segmentation
        features = ['total_revenue', 'avg_deal_size', 'total_deals']
        X = customers_df[features].fillna(0)
        
        # Normalize data
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Simple segmentation based on revenue and engagement
        customers_df['segment'] = np.where(
            (X_scaled[:, 0] > 0.7) & (X_scaled[:, 2] > 0.7),
            'High Value',
            np.where(
                (X_scaled[:, 0] > 0.3) & (X_scaled[:, 2] > 0.3),
                'Medium Value',
                'Low Value'
            )
        )
        
        # Display segments
        fig = px.scatter(customers_df, 
                        x='total_revenue',
                        y='total_deals',
                        color='segment',
                        title='Customer Segmentation',
                        hover_data=['name'])
        st.plotly_chart(fig)
        
        # Segment analysis
        st.write("Segment Analysis")
        segment_analysis = customers_df.groupby('segment').agg({
            'id': 'count',
            'total_revenue': 'sum',
            'avg_deal_size': 'mean'
        }).round(2)
        st.dataframe(segment_analysis)
        
def main():
    if not login():
        return
    
    st.title("CRM System")
    
    # Main category tabs
    main_tabs = st.tabs([
        "Dashboard",
        "Customer Management",
        "Sales Management",
        "Analytics & Reporting",
        "Marketing Tools",
        "System Tools"
    ])
    
    # Dashboard Tab
    with main_tabs[0]:
        show_dashboard()
    
    # Customer Management Tab
    with main_tabs[1]:
        customer_section = st.selectbox(
            "Select Customer Management Area",
            ["Customers", "Communications", "Segmentation", "Lead Scoring", "Meeting Management"]
        )
        
        if customer_section == "Customers":
            tab1, tab2 = st.tabs(["Add Customer", "View Customers"])
            with tab1:
                add_customer()
            with tab2:
                view_customers()
        elif customer_section == "Communications":
            tab1, tab2 = st.tabs(["Send Communication", "Email Templates"])
            with tab1:
                manage_communications()
            with tab2:
                manage_email_templates()
        elif customer_section == "Segmentation":
            customer_segmentation()
        elif customer_section == "Lead Scoring":
            lead_scoring()
        elif customer_section == "Meeting Management":
            meeting_management()
    
    # Sales Management Tab
    with main_tabs[2]:
        sales_section = st.selectbox(
            "Select Sales Management Area",
            ["Deals", "Tasks", "Calendar", "Documents"]
        )
        
        if sales_section == "Deals":
            manage_deals()
        elif sales_section == "Tasks":
            manage_tasks()
        elif sales_section == "Calendar":
            calendar_management()
        elif sales_section == "Documents":
            document_management()
    
    # Analytics & Reporting Tab
    with main_tabs[3]:
        analytics_section = st.selectbox(
            "Select Analytics Area",
            ["Analytics Dashboard", "Sales Forecasting", "Performance Metrics"]
        )
        
        if analytics_section == "Analytics Dashboard":
            show_enhanced_analytics()
        elif analytics_section == "Sales Forecasting":
            sales_forecasting()
        elif analytics_section == "Performance Metrics":
            performance_dashboard()
    
    # Marketing Tools Tab
    with main_tabs[4]:
        marketing_section = st.selectbox(
            "Select Marketing Area",
            ["Marketing Campaigns", "Content Management", "Form Builder", "SEO Tools"]
        )
        
        if marketing_section == "Marketing Campaigns":
            marketing_campaigns()
        elif marketing_section == "Content Management":
            content_management()
        elif marketing_section == "Form Builder":
            form_builder()
        elif marketing_section == "SEO Tools":
            seo_tools()
    
    # System Tools Tab
    with main_tabs[5]:
        system_section = st.selectbox(
            "Select System Area",
            ["Team Collaboration", "Automation", "Workflow Automation", "Data Management"]
        )
        
        if system_section == "Team Collaboration":
            team_collaboration()
        elif system_section == "Automation":
            automation_rules()
        elif system_section == "Workflow Automation":
            workflow_automation()
        elif system_section == "Data Management":
            tab1, tab2 = st.tabs(["Custom Fields", "Import/Export"])
            with tab1:
                manage_custom_fields()
            with tab2:
                import_export_data()

if __name__ == "__main__":
    update_advanced_schema()
    main()
