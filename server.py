import socket
import sqlite3
import threading

HOST = '0.0.0.0'
port = 5555
DB_FILE = 'locker_data.db'
ADDRESS_SPACE = 7   # set at start
ID_SIZE = 48

def protocolWrapper(code, addr, status, response=0):
    if code == "OK":
        code_wrap = 1
    elif code == "BD":
        code_wrap = 0
    else:
        return False
    
    string_addr = str(addr)
    if len(string_addr) < ADDRESS_SPACE:
        string_addraddr = f"{(ADDRESS_SPACE - len(string_addr)) * '0'}{string_addr}"
    
    return f"{code_wrap}{string_addr}{status}{response}\n".encode('utf-8')

def protocolUnwrapper(request):
    data = []
    cmd = int(request[0])
    if cmd:
        data.append("GET")
    else:
        data.append("PUT")

    data.append(request[1:ADDRESS_SPACE+1])
    data.append(request[ADDRESS_SPACE+1 : ADDRESS_SPACE+ID_SIZE+1])
    
    type_re = int(request[ADDRESS_SPACE+ID_SIZE+1 :])
    match(type_re):
        case 0:
            data.append("MTCH")
        case 1:
            data.append("STAT")
        case 2:
            data.append("BLNK")
        case 3:
            data.append("ALL")
    
    return data
        
def response(client_obj, code, addr, status, response=0):
    try:
        reply = protocolWrapper(code, addr, status, response)
        if reply:
            client_obj.send(reply)
    except Exception as e:
        print(f"Failed to send response: {e}")
    finally:
        client_obj.close()

def handle_client(client, addr):
    """
    WORKER THREAD: Handles a single connection from start to finish.
    """
    conn = sqlite3.connect(DB_FILE, timeout=5.0)
    conn.execute('PRAGMA synchronous=NORMAL;')
    cursor = conn.cursor()
    
    try:
        with client:
            data = client.recv(1024).decode('utf-8').strip()
            if not data:
                return

            info = protocolUnwrapper(data)
            if len(info) < 4:
                return
                
            cmd = info[0]
            address = int(info[1])
            cmd_type = info[3]
            id_hex = int(info[2], 16)

            if cmd == "GET":
                if cmd_type == 'MTCH':
                    cursor.execute('SELECT id_num FROM locker_data WHERE address = ?',(address,))
                    row = cursor.fetchone()
                    if row:
                        if row[0] == id_hex:
                            response(client, 'OK', address, 0, 1)
                            cursor.execute('''
                                UPDATE locker_data
                                SET status = 0, id_num = 0
                                WHERE address = ?
                            ''',(address,))
                            conn.commit()
                        else:
                            response(client, 'OK', address, 1, 0)
                    else:
                        response(client, 'BD', address, 1, 0)
                        
                elif cmd_type == "STAT":
                    cursor.execute('SELECT status FROM locker_data WHERE address = ?',(address,))
                    row = cursor.fetchone()
                    if row:
                        response(client, 'OK', address, row[0], 0)
                    else:
                        response(client, "BD", address, 0, 0)
                        
            elif cmd == "PUT":
                cursor.execute('''
                    INSERT INTO locker_data (address, status, id_num, start_time) 
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(address) DO UPDATE SET 
                    status = excluded.status,
                    id_num = excluded.id_num,
                    start_time = CURRENT_TIMESTAMP
                    ''', (address, 1, id_hex))
                conn.commit()
                response(client, "OK", address, 1, 0)
                
    except Exception as e:
        print(f"Error handling node {addr}: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        # --- NEW: Enable Write-Ahead Logging (WAL) globally before starting the server ---
        with sqlite3.connect(DB_FILE) as temp_conn:
            temp_conn.execute('PRAGMA journal_mode=WAL;')
            
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen()
        print(f"Initialized and listening on port {port}...")

        while True:
            # Main thread strictly accepts connections and assigns them to worker threads
            client, addr = server.accept()
            
            # Create and start a new thread for this specific client
            client_thread = threading.Thread(target=handle_client, args=(client, addr))
            # daemon=True ensures threads don't block the server from shutting down
            client_thread.daemon = True 
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\nServer shutting down...")              
    finally:
        if 'server' in locals():
            server.close()
