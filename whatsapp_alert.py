import pywhatkit as kit
import time
import pyautogui
from pynput.keyboard import Key, Controller

keyboard = Controller()

def send_bulk_whatsapp_notifications(absentees):
    """
    Sends messages using pywhatkit by automating the browser.
    Note: Requires WhatsApp Web to be logged in on the default browser.
    """
    success_count = 0
    
    for student in absentees:
        name = student['Name']
        regno = student['RegNo']
        # Ensure number starts with '+' and country code, e.g., '+911234567890'
        phone_number = student['Parent_WhatsApp']
        
        message = (
            f"Dear Parent, "
            f"Your ward {name} (Reg No: {regno}) was absent today."
            f"-- Automated Attendance System"
        )
        
        try:
            # sendwhatmsg_instantly parameters:
            # phone_no, message, wait_time (seconds), tab_close (bool), close_time (seconds)
            kit.sendwhatmsg_instantly(
                phone_no=phone_number,
                message=message,
                wait_time=15, # Time for WhatsApp Web to load
                tab_close=True,
                close_time=3
            )
            
            # pywhatkit sometimes needs a small manual 'Enter' trigger depending on the OS/Browser
            time.sleep(2)
            pyautogui.press('enter')  # Simulate pressing 'Enter' to send the message
            #keyboard.press(Key.enter)
            #keyboard.release(Key.enter)
            
            success_count += 1
            # Add a buffer between students to avoid WhatsApp spam detection
            time.sleep(5) 
            
        except Exception as e:
            print(f"Error sending to {name}: {e}")
            
    return success_count