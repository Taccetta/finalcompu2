import socket
import threading
from threading import Semaphore
import json
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.units import mm
from dotenv import load_dotenv
from datetime import datetime
from multiprocessing import Process, Queue
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
import time
import select #select protocolo ip

#=================================================================================
# env
load_dotenv()
HOST = os.getenv('HOST')
PORT = int(os.getenv('PORT'))

# mutex
log_lock = threading.Lock()

# db
Base = declarative_base()

class ConversionLog(Base):
    __tablename__ = 'conversiones'
    id = Column(Integer, primary_key=True)
    ip = Column(String(15))
    nombre_archivo = Column(String(255))
    tamano_txt = Column(Integer)  # En bytes
    tamano_pdf = Column(Integer)  # En bytes
    fecha = Column(DateTime)

# db config
engine = create_engine('sqlite:///conversiones.db')
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# Cola IPC proceso DB
db_queue = Queue()
#=================================================================================

def generar_pdf(txt_path, pdf_path):
    """TXT a PDF"""
    try:
        # margenes
        doc = SimpleDocTemplate(pdf_path, 
                               pagesize=A4,
                               leftMargin=20*mm,
                               rightMargin=20*mm,
                               topMargin=20*mm,
                               bottomMargin=20*mm)
        
        # estilo
        styles = getSampleStyleSheet()
        estilo_cuerpo = ParagraphStyle(
            'Cuerpo',
            parent=styles['Normal'],
            fontSize=12,
            leading=14,
            alignment=TA_JUSTIFY,
            splitLongWords=True,
            hyphenation=True
        )
        
        # formatear
        contenido = []
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = ' '.join(line.strip().split())
                if line:  
                    contenido.append(Paragraph(line, estilo_cuerpo))
        
        # PDF
        doc.build(contenido)
    except Exception as e:
        raise RuntimeError(f"Error al generar PDF: {str(e)}")

def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        # ID hilo
        thread_id = threading.get_ident()
        
        # metadatos
        header_data = conn.recv(1024).strip()
        if not header_data:
            return
        header = json.loads(header_data.decode('utf-8'))
        
        # chequeos
        if header['conversion_type'] != 'txt2pdf':
            raise ValueError("Tipo de conversión no soportado")
            
        file_name = header['file_name']
        if not file_name.lower().endswith('.txt'):
            raise ValueError("El archivo debe ser .txt")
        file_size = header['file_size']
        
        # ruta de guardado
        temp_input = os.path.join('temp', f"{thread_id}_{file_name}")
        os.makedirs('temp', exist_ok=True)

        #os.system("pause")
        
        with open(temp_input, 'wb') as f:
            remaining = file_size
            while remaining > 0:
                try:
                    data = conn.recv(min(4096, remaining))
                    #os.system("pause")
                    if not data:
                        raise ConnectionError("Cliente desconectado durante la transferencia del archivo")
                    f.write(data)
                    remaining -= len(data)
                except (ConnectionResetError, BrokenPipeError):
                    raise ConnectionError("Conexión interrumpida durante la recepción del archivo")
        
        # PDF
        output_name = f"{thread_id}_{file_name[:-4]}.pdf"
        output_path = os.path.join('temp', output_name)
        generar_pdf(temp_input, output_path)
        
        # Enviar datos a DB Worker
        db_data = {
            'ip': addr[0],
            'nombre_archivo': file_name[:-4],
            'tamano_txt': os.path.getsize(temp_input),
            'tamano_pdf': os.path.getsize(output_path),
            'fecha': datetime.now()
        }
        db_queue.put(db_data)
        
        # Enviar respuesta
        with open(output_path, 'rb') as f:
            pdf_data = f.read()
            response_header = {
                'file_name': output_name,
                'file_size': len(pdf_data)
            }
            response_header_json = json.dumps(response_header).encode('utf-8')
            response_header_json += b' ' * (1024 - len(response_header_json))
            
            try:
                # Enviar encabezado
                conn.sendall(response_header_json)
                
                # Enviar datos en bloques con verificación
                total_sent = 0
                while total_sent < len(pdf_data):
                    chunk = pdf_data[total_sent:total_sent+4096]
                    sent = conn.send(chunk)
                    if sent == 0:
                        raise ConnectionError("Conexión cerrada por el cliente durante el envío")
                    total_sent += sent
                    
            except (ConnectionResetError, BrokenPipeError, TimeoutError) as e:
                raise ConnectionError("Error de conexión durante el envío del PDF") from e
            
        # Registro mutex exitoso
        with log_lock:
            with open('log_send.txt', 'a', encoding='utf-8') as log_file:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"[{timestamp}] Hilo {thread_id} - Archivo {output_name} enviado exitosamente\n"
                log_file.write(log_entry)
            
            db_data = {
                'ip': addr[0],
                'nombre_archivo': file_name[:-4],
                'tamano_txt': os.path.getsize(temp_input),
                'tamano_pdf': os.path.getsize(output_path),
                'fecha': datetime.now()
            }
            db_queue.put(db_data)
            
    except ConnectionError as e:
        error_msg = f"Error de conexión: {str(e)}"
        with log_lock:
            with open('log_send.txt', 'a', encoding='utf-8') as log_file:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"[{timestamp}] Hilo {thread_id} - {error_msg}\n"
                log_file.write(log_entry)
        
        try:
            error_header = {'error': error_msg, 'file_size': 0}
            error_header_json = json.dumps(error_header).encode('utf-8')
            error_header_json += b' ' * (1024 - len(error_header_json))
            conn.sendall(error_header_json)
        except:
            pass
    finally:
        # cleaner
        if 'temp_input' in locals():
            try: os.remove(temp_input)
            except: pass
        if 'output_path' in locals():
            try: os.remove(output_path)
            except: pass
        conn.close()

def check_exit_command():
    """Monitor de exit"""
    while True:
        command = input().strip().lower()
        if command == 'exit':
            print("Cerrando servidor y procesos hijos...")
            # Enviar señal de terminación al proceso de DB
            db_queue.put(None)
            # Dar tiempo para que se cierre ordenadamente
            time.sleep(1)
            os._exit(0)

def db_worker(queue):
    """Proceso hijo DB"""
    while True:
        try:
            data = queue.get()
            if data is None:  # Señal de terminación
                print("Cerrando proceso de base de datos...")
                break
                
            session = Session()
            registro = ConversionLog(
                ip=data['ip'],
                nombre_archivo=data['nombre_archivo'],
                tamano_txt=data['tamano_txt'],
                tamano_pdf=data['tamano_pdf'],
                fecha=data['fecha']
            )
            session.add(registro)
            session.commit()
            session.close()
        except Exception as e:
            print(f"Error en DB Worker: {str(e)}")
        finally:
            Session.remove()

def start_server():
    # proceso db
    db_process = Process(target=db_worker, args=(db_queue,))
    db_process.start()
    
    try:
        # hilo monitor de comandos
        exit_thread = threading.Thread(target=check_exit_command, daemon=True)
        exit_thread.start()
    
        # Crear sockets para todas las familias disponibles
        sockets = []
        families = set()
        
        # Obtener direcciones disponibles
        for res in socket.getaddrinfo(None, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            
            try:
                s = socket.socket(af, socktype, proto)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(sa)
                s.listen()
                sockets.append(s)
                families.add(af)
            except OSError as e:
                if s:
                    s.close()
                print(f"Error creando socket para familia {af}: {e}")
        
        if not sockets:
            raise RuntimeError("No se pudo crear ningún socket (IPv4/IPv6 no disponibles)")
        
        print(f"Server listening on:")
        for s in sockets:
            print(f" - {s.getsockname()} ({'IPv4' if s.family == socket.AF_INET else 'IPv6'})")
        
        while True:
            # select para manejar múltiples sockets
            readable, _, _ = select.select(sockets, [], [])
            for s in readable:
                conn, addr = s.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()
    
    finally:
        # Cerrar todos los sockets
        for s in sockets:
            s.close()
        # Asegurar cierre del proceso hijo
        db_process.terminate()
        db_process.join()

if __name__ == '__main__':
    start_server()