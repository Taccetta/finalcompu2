import argparse
import socket
import json
import os
import sys



def parse_arguments():
    """Configura y parsea los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Cliente para conversión TXT a PDF')
    parser.add_argument('--ip', required=True,
                        help='Dirección IP del servidor (IPv4 o IPv6)')
    parser.add_argument('--port', type=int, required=True,
                        help='Puerto del servidor (1-65535)')
    parser.add_argument('--file_path', required=True,
                        help='Ruta al archivo .txt a convertir')
    return parser.parse_args()

def validate_input(args):
    """Valida los argumentos recibidos"""
    # Validar puerto
    if not (1 <= args.port <= 65535):
        raise ValueError("Puerto fuera de rango válido (1-65535)")
        
    # Validar archivo
    if not args.file_path.lower().endswith('.txt'):
        raise ValueError("El archivo debe tener extensión .txt")
    if not os.path.isfile(args.file_path):
        raise ValueError(f"Archivo no encontrado: {args.file_path}")
    
    # Validar IP
    try:
        socket.inet_pton(socket.AF_INET, args.ip)
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, args.ip)
        except socket.error:
            raise ValueError("Dirección IP no válida (IPv4 o IPv6)")

def send_file(file_path, server_ip, server_port):
    # Validar
    if not file_path.lower().endswith('.txt'):
        print("Error: El archivo debe ser .txt")
        return

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    # IPv4 o IPv6
    try:
        socket.inet_pton(socket.AF_INET, server_ip)
        addr_family = socket.AF_INET
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, server_ip)
            addr_family = socket.AF_INET6
        except socket.error:
            print("Error: Dirección IP no válida")
            return

    with socket.socket(addr_family, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(120)
            s.connect((server_ip, server_port))
            print(f"Conectado al servidor [{server_ip}]:{server_port} usando {'IPv6' if addr_family == socket.AF_INET6 else 'IPv4'}")
        except (ConnectionRefusedError, socket.timeout) as e:
            print(f"Error de conexión: No se pudo conectar al servidor {server_ip}:{server_port}")
            print(f"Detalles: {str(e)}")
            return
        except Exception as e:
            print(f"Error inesperado al conectar: {str(e)}")
            return
            
        print(f"Conectado al servidor {server_ip}:{server_port}")
        
        # envio de metadatos
        header = {
            'conversion_type': 'txt2pdf',
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

if __name__ == '__main__':
    try:
        args = parse_arguments()
        validate_input(args)
        send_file(args.file_path, args.ip, args.port)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)