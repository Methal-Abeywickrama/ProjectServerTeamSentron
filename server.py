import socket
import sqlite3

HOST = '0.0.0.0'
port = 5555
DB_FILE = 'locker_data.db'

def response(client_obj, code, addr, status, response=0):
    try:
        client_obj.send(f"{code} {addr} {status} {response}\n".encode('utf-8'))
    except Exception as e:
        print(f"Failed to send response: {e}")
    finally:
        client_obj.close()

if __name__ == "__main__":
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen()
        print("Initialized...")

        while True:
            client, addr = server.accept()
            with client:
                data = client.recv(1024).decode('utf-8').strip()
                if not data:
                    continue

                info = data.split(" ")
                cmd = info[0]
                address = int(info[1])
                cmd_type = info[2]
                id_hex = int(info[3], 16)

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
    except KeyboardInterrupt:
        print("\nServer shutting down...")              
    finally:
        # Gracefully close connections on shutdown
        if 'conn' in locals():
            conn.close()
        if 'server' in locals():
            server.close()
                
