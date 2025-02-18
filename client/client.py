import argparse
import socket
import json
import os

# colocar al parseo
HOST = 'localhost'
PORT = 5000

def send_file(conversion_type, file_path):
    # Validar
    if not file_path.lower().endswith('.txt'):
        print("Error: El archivo debe ser .txt")
        return

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Conectado al servidor {HOST}:{PORT}")
        
        # envio de metadatos
        header = {
            'conversion_type': conversion_type,
            'file_name': file_name,
            'file_size': file_size
        }
        header_json = json.dumps(header).encode('utf-8')
        header_json += b' ' * (1024 - len(header_json))
        s.sendall(header_json)
        print(f"Enviando archivo: {file_name} ({file_size} bytes)")
        
        # envio TXT
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                s.sendall(data)
        
        # respuesta
        response_header_data = s.recv(1024).strip()
        if not response_header_data:
            print("Sin respuesta del servidor")
            return
            
        response_header = json.loads(response_header_data.decode('utf-8'))
        
        if 'error' in response_header:
            print(f"Error del servidor: {response_header['error']}")
            return
            
        output_file = response_header['file_name']
        output_size = response_header['file_size']
        
        # recibir PDF completo
        pdf_data = b''
        while len(pdf_data) < output_size:
            chunk = s.recv(4096)
            if not chunk:
                break
            pdf_data += chunk
        
        if len(pdf_data) == output_size:
            with open(output_file, 'wb') as f:
                f.write(pdf_data)
            print(f"PDF generado exitosamente: {output_file} ({output_size} bytes)")
        else:
            print("Error: Archivo PDF incompleto recibido")

def main():
    parser = argparse.ArgumentParser(description='Conversor TXT a PDF')
    parser.add_argument('--conversion_type', choices=['txt2pdf'], required=True,
                       help='Tipo de conversión (solo txt2pdf)')
    parser.add_argument('--file_path', required=True, 
                       help='Ruta al archivo .txt de entrada')
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        print(f"Error: Archivo {args.file_path} no encontrado")
        return
    
    send_file(args.conversion_type, args.file_path)

if __name__ == '__main__':
    main()