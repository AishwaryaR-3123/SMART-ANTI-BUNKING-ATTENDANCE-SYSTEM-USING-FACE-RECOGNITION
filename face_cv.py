import cv2
import face_recognition
import numpy as np
import json
import streamlit as st
from database import get_db_connection, mark_student_present
from datetime import datetime

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def load_known_faces():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT RegNo, Name, Face_Encoding FROM students_info")
    records = cursor.fetchall()
    conn.close()
    
    known_encodings = []
    known_regnos = []
    known_names = []
    
    for row in records:
        if row['Face_Encoding']:
            encoding = np.frombuffer(row['Face_Encoding'], dtype=np.float64)
            known_encodings.append(encoding)
            known_regnos.append(row['RegNo'])
            known_names.append(row['Name'])
            
    return known_encodings, known_regnos, known_names

def run_attendance_camera(date_str, end_time, placeholder):
    """
    Runs the webcam, compares faces, updates DB, and stops at end_time.
    Uses a Streamlit placeholder to render frames without rerunning the whole script.
    """
    known_encodings, known_regnos, known_names = load_known_faces()
    cap = cv2.VideoCapture(0)
    
    # Keep track of who has been marked to avoid spamming the DB
    marked_today = set()
    
    while datetime.now() < end_time:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to access webcam.")
            break
            
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find faces
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Unknown"
            
            if True in matches:
                first_match_index = matches.index(True)
                regno = known_regnos[first_match_index]
                name = known_names[first_match_index]
                
                # Mark attendance if not already marked in this session
                if regno not in marked_today:
                    mark_student_present(regno, date_str)
                    marked_today.add(regno)
            
            # Scale back up face locations and draw box
            top *= 4; right *= 4; bottom *= 4; left *= 4
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
            
        # Display the frame in Streamlit
        placeholder.image(frame, channels="BGR", width="stretch")
        
    cap.release()
    placeholder.empty() # Clear camera feed when done
    return len(marked_today)