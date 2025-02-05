import socket
import threading
import json
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.units import mm

HOST = 'localhost'
PORT = 5000

def generar_pdf(txt_path, pdf_path):
    """Convierte TXT a PDF con formato profesional"""
    try:
        # Configurar documento
        doc = SimpleDocTemplate(pdf_path, 
                               pagesize=A4,
                               leftMargin=20*mm,
                               rightMargin=20*mm,
                               topMargin=20*mm,
                               bottomMargin=20*mm)
        
        # Crear estilo personalizado
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
        
        # Leer y formatear contenido
        contenido = []
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Convertir espacios múltiples en uno solo
                line = ' '.join(line.strip().split())
                if line:  # Ignorar líneas vacías
                    contenido.append(Paragraph(line, estilo_cuerpo))
        
        # Generar PDF
        doc.build(contenido)
    except Exception as e:
        raise RuntimeError(f"Error al generar PDF: {str(e)}")

def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        # Recibir metadatos
        header_data = conn.recv(1024).strip()
        if not header_data:
            return
        header = json.loads(header_data.decode('utf-8'))
        
        # Validar tipo de conversión
        if header['conversion_type'] != 'txt2pdf':
            raise ValueError("Tipo de conversión no soportado")
            
        file_name = header['file_name']
        if not file_name.lower().endswith('.txt'):
            raise ValueError("El archivo debe ser .txt")
            
        file_size = header['file_size']
        
        # Recibir archivo TXT
        temp_input = os.path.join('temp', file_name)
        os.makedirs('temp', exist_ok=True)
        
        with open(temp_input, 'wb') as f:
            remaining = file_size
            while remaining > 0:
                data = conn.recv(min(4096, remaining))
                if not data:
                    break
                f.write(data)
                remaining -= len(data)
        
        # Generar PDF
        output_name = file_name[:-4] + '.pdf'
        output_path = os.path.join('temp', output_name)
        generar_pdf(temp_input, output_path)
        
        # Enviar PDF
        with open(output_path, 'rb') as f:
            pdf_data = f.read()
            response_header = {
                'file_name': output_name,
                'file_size': len(pdf_data)
            }
            response_header_json = json.dumps(response_header).encode('utf-8')
            response_header_json += b' ' * (1024 - len(response_header_json))
            conn.sendall(response_header_json)
            conn.sendall(pdf_data)
            
    except Exception as e:
        error_header = {'error': str(e), 'file_size': 0}
        error_header_json = json.dumps(error_header).encode('utf-8')
        error_header_json += b' ' * (1024 - len(error_header_json))
        conn.sendall(error_header_json)
    finally:
        # Limpiar archivos temporales
        if 'temp_input' in locals():
            try: os.remove(temp_input)
            except: pass
        if 'output_path' in locals():
            try: os.remove(output_path)
            except: pass
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == '__main__':
    start_server()