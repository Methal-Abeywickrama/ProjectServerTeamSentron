import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import sqlite3
import threading
import time

DB_FILE = 'locker_data.db'

# 1. Initialize Firebase
cred = credentials.Certificate('firebase_credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. Function to update local SQLite when Firebase changes
def on_snapshot(col_snapshot, changes, read_time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    for change in changes:
        if change.type.name in ['ADDED', 'MODIFIED']:
            doc = change.document.to_dict()
            locker_address = change.document.id
            
            # If the app books a locker, it sets a remote ID and status
            if doc.get('remote_booked') == True:
                user_id = doc.get('user_id', 0)
                
                print(f"Cloud update received: Booking locker {locker_address} for ID {user_id}")
                
                # Update local database to reserve it
                cursor.execute('''
                    INSERT INTO locker_data (address, status, id_num, start_time) 
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(address) DO UPDATE SET 
                    status = excluded.status,
                    id_num = excluded.id_num,
                    start_time = CURRENT_TIMESTAMP
                ''', (locker_address, 1, user_id))
                conn.commit()

    conn.close()

# 3. Setup Firestore Listener
col_query = db.collection('lockers')
query_watch = col_query.on_snapshot(on_snapshot)

# 4. Function to sync local hardware changes UP to Firebase
def sync_local_to_cloud():
    while True:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT address, status FROM locker_data")
            rows = cursor.fetchall()
            
            for row in rows:
                address = str(row[0]).zfill(3) # Format as '001', '002'
                status = row[1]
                
                # Update Firebase with the current physical status
                db.collection('lockers').document(address).set({
                    'physical_status': status,
                    'last_updated': firestore.SERVER_TIMESTAMP
                }, merge=True)
                
            conn.close()
        except Exception as e:
            print(f"Sync error: {e}")
            
        time.sleep(5) # Push state every 5 seconds

if __name__ == "__main__":
    print("Starting Firebase Sync Service...")
    # Start the upward sync in a background thread
    sync_thread = threading.Thread(target=sync_local_to_cloud, daemon=True)
    sync_thread.start()
    
    # Keep the main thread alive to maintain the Firestore listener
    while True:
        time.sleep(1)