import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import face_recognition
import cv2
import os

from database import authenticate_user, register_student, ensure_date_column_exists, get_absentees_for_date, get_db_connection
from face_cv import run_attendance_camera
from whatsapp_alert import send_bulk_whatsapp_notifications

# --- CACHING FUNCTIONS ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_get_attendance_data():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM attendance", conn)
    conn.close()
    return df

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def cached_load_known_faces():
    from face_cv import load_known_faces
    return load_known_faces()

# Initialize Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'username' not in st.session_state:
    st.session_state.username = None

# --- AUTHENTICATION ---
def login_page():
    st.image("Assets\\Nevermore Academy Smart Attendance System.png")
    #st.title("Smart Anti-Bunking Attendance System Using Face Recognition")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            user = authenticate_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_role = user['designation']
                st.session_state.username = user['username']
                st.session_state.name = user['name']
                st.rerun()
            else:
                st.error("Invalid Username or Password")

# --- ADMIN / FACULTY DASHBOARD ---
def admin_dashboard():
    st.sidebar.title(f"Welcome {st.session_state.name}!")
    menu = st.sidebar.selectbox("Menu", ["Mark Attendance", "Register Student", "View Attendance"])
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if menu == "Mark Attendance":
        st.image("Assets\\Nevermore Academy Smart Attendance System.png")
        st.header("Start Attendance Session")
        
        col1, col2 = st.columns(2)
        with col1:
            duration = st.number_input("Session Duration (minutes)", min_value=1, max_value=60, value=5)
        
        if st.button("Start Camera & Attendance"):
            date_str = datetime.now().strftime("%d-%m-%y")
            ensure_date_column_exists(date_str)
            
            end_time = datetime.now() + timedelta(minutes=duration)
            st.info(f"Attendance running until {end_time.strftime('%H:%M:%S')}")
            
            # Placeholder for camera feed
            camera_placeholder = st.empty()
            
            # Blocking call: Runs camera until end_time
            marked_count = run_attendance_camera(date_str, end_time, camera_placeholder)
            
            st.success(f"Attendance session ended! {marked_count} students marked present.")
            
            # Trigger WhatsApp Notifications
            with st.spinner("Identifying absentees and sending WhatsApp notifications..."):
                absentees = get_absentees_for_date(date_str)
                success_msgs = send_bulk_whatsapp_notifications(absentees)
                st.success(f"Sent {success_msgs} WhatsApp notifications to parents of absent students.")

    elif menu == "Register Student":
        st.image("Assets\\Nevermore Academy Smart Attendance System.png")
        st.header("Register New Student")
        with st.form("register_form", clear_on_submit=True):
            regno_input = st.text_input("Register Number")
            name = st.text_input("Name")
            dept = st.text_input("Department")
            parent_whatsapp = st.text_input("Parent WhatsApp (+91...)")
            username = st.text_input("Student Login Username")
            password = st.text_input("Student Login Password", type="password")
            
            image_file = st.file_uploader("Upload Student Photo", type=["jpg", "jpeg", "png"])
            submit = st.form_submit_button("Register")
            
            if submit and image_file:
                regno = int(regno_input)

                try:
                    regno = int(regno_input)
            
                    if not os.path.exists("Face_Encodings"):
                        os.makedirs("Face_Encodings")

                    # 1. HARD-SAVE the raw upload straight to your hard drive. 
                    # No PIL, no Streamlit memory tricks. Just a pure file dump.
                    temp_path = f"Face_Encodings/temp_{regno}.jpg"
                    with open(temp_path, "wb") as f:
                        f.write(image_file.getbuffer())

                    # 2. Read it back directly from the hard drive using OpenCV.
                    # This completely severs the link to Streamlit's weird memory formatting.
                    img = cv2.imread(temp_path)

                    if img is None:
                        st.error("The image file itself is corrupted. Please download a fresh JPG from Google and try that.")
                    else:
                        # 3. OpenCV reads as BGR. Convert to standard RGB for dlib.
                        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                        # 4. Extract the face encoding
                        encodings = face_recognition.face_encodings(rgb_img)

                        if len(encodings) > 0:
                            face_encoding = encodings[0]
                            
                            # 5. Rename to the final path and clean up
                            final_path = f"Face_Encodings/{regno}.jpg"
                            cv2.imwrite(final_path, img) 
                            if os.path.exists(temp_path):
                                os.remove(temp_path)

                            # 6. Save to Database
                            success = register_student(
                                regno, name, dept, parent_whatsapp, face_encoding, username, password
                            )

                            if success:
                                st.success("Student Registered Successfully!")
                            else:
                                st.error("Failed to save to database. Check if RegNo or Username already exists.")
                        else:
                            st.error("No face found in the uploaded image. Please try a clearer photo.")
                            
                except Exception as e:
                    st.error(f"Image processing error: {e}")
                
    elif menu == "View Attendance":
        st.image("Assets\\Nevermore Academy Smart Attendance System.png")
        st.header("Attendance Reports")
        df = cached_get_attendance_data()
        
        date_str = datetime.now().strftime("%d-%m-%y")
        if date_str in df.columns:
            total = len(df)
            present = df[date_str].sum()
            absent = total - present
            
            st.subheader(f"Today's Statistics ({date_str})")
            c1, c2, c3 = st.columns(3)
            c1.metric("On Roll", total)
            c2.metric("Present", present)
            c3.metric("Absent", absent)
            
        st.dataframe(df)
        
        # Export to Excel
        output_file = "attendance_report.xlsx"
        df.to_excel(output_file, index=False)
        with open(output_file, "rb") as file:
            st.download_button("Download as Excel", data=file, file_name=output_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- STUDENT DASHBOARD ---
def student_dashboard():
    st.sidebar.title(f"Welcome {st.session_state.name}!")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.image("Assets\\Nevermore Academy Smart Attendance System.png")    
    st.header("My Attendance Dashboard")
    
    conn = get_db_connection()
    # Fetch student details via username -> login_credentials -> students_info
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.* FROM attendance a
        JOIN login_credentials l ON a.name = l.name 
        WHERE l.username = %s
    """, (st.session_state.username,))
    
    student_record = cursor.fetchone()
    conn.close()
    
    if student_record:
        # Extract dynamic date columns (skip Regno and name)
        date_cols = [col for col in student_record.keys() if col not in ('regno', 'name')]
        
        total_days = len(date_cols)
        days_present = sum([student_record[col] for col in date_cols if student_record[col] == 1])
        days_absent = total_days - days_present
        attendance_percentage = (days_present / total_days * 100) if total_days > 0 else 0
        
        st.subheader(f"RegNo: {student_record['RegNo']} | Name: {student_record['Name']}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Working Days", total_days)
        col2.metric("Days Present", days_present)
        col3.metric("Days Absent", days_absent)
        col4.metric("Attendance %", f"{attendance_percentage:.1f}%")
        
    else:
        st.warning("No attendance records found.")

# --- ROUTING LOGIC ---
if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.user_role in ['Admin', 'Faculty']:
        admin_dashboard()
    elif st.session_state.user_role == 'Student':
        student_dashboard()