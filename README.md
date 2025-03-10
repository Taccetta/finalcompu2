# **EXAMEN FINAL - COMPUTACIÓN 2 - TACCETTA**

## Objetivos del Programa

El objetivo de este programa es proporcionar un servicio de conversión de archivos de texto (TXT) a archivos PDF. El servidor recibe archivos TXT de los clientes, los convierte a PDF y devuelve el archivo PDF generado. Además, registra las conversiones en una base de datos y mantiene un log de las operaciones realizadas.

## Arquitectura del Sistema
![Arquitectura](https://imgur.com/a/FXlHGtA "Arquitectura")

El sistema está diseñado como una arquitectura cliente-servidor con capacidades de concurrencia y multiprocesamiento para manejar múltiples solicitudes simultáneas. A continuación se describe brevemente la arquitectura:

### Cliente:
**Responsabilidad:** Envía archivos TXT al servidor para su conversión a PDF.

**Componentes**:
- **Interfaz de Línea de Comandos**: Permite al usuario especificar la dirección IP, el puerto y la ruta del archivo TXT.
- **Validación**: Verifica la validez de los argumentos proporcionados antes de enviar el archivo.
- **Comunicación**: Utiliza sockets para conectarse al servidor y enviar/recibir datos.

### Servidor:
**Responsabilidad**: Recibe archivos TXT de los clientes, los convierte a PDF y devuelve el archivo PDF generado.

**Componentes:**
- **Socket Server**: Escucha en múltiples direcciones IP (IPv4 e IPv6) para aceptar conexiones entrantes, permitiendo la comunicación bidireccional entre el cliente y el servidor, mediante JSON para la estructuración de datos
- **Concurrencia y Multiprocesamiento:**
-- **Hilos de Trabajo**: Cada conexión de cliente se maneja en un hilo separado para permitir la concurrencia, y mejorando la eficiencia del servidor.
-- **Procesos**: El proceso de base de datos se ejecuta de manera independiente para mejorar la modularidad y la eficiencia.
- **Generador de PDF**: Utiliza la biblioteca reportlab para convertir archivos TXT a PDF.
- **Base de Datos**: Registra los detalles de cada conversión en una base de datos SQLite.
- **Proceso de Base de Datos**: Ejecuta en un proceso separado para manejar las operaciones de base de datos de manera independiente.
- **Cola IPC**: Facilita la comunicación entre el servidor principal y el proceso de base de datos.
- **Mutex**: Asegura el acceso exclusivo a recursos compartidos y evitando condiciones de carrera, como el archivo de log.

### Tareas a EjecutarTareas a Ejecutar
**1. Generar PDF (*generar_pdf*)**
Convierte un archivo .txt en un archivo .pdf utilizando la biblioteca reportlab. Se formatea el texto para mantener un aspecto limpio y profesional en el PDF.

**2. Manejar Cliente (*handle_client*)**
Gestiona la conexión con el cliente. Recibe el archivo .txt, lo guarda temporalmente, realiza la conversión y envía el PDF resultante al cliente.

**3. Monitor de Salida (*check_exit_command*)**
Permite detener el servidor manualmente mediante el comando exit.

**4. Proceso de Base de Datos (*db_worker*)**
Inserta en la base de datos los registros de las conversiones realizadas.

**5. Iniciar el Servidor (*start_server*)**
Configura el servidor para aceptar conexiones tanto en IPv4 como en IPv6, utilizando múltiples sockets para manejar distintas conexiones simultáneamente.

### Instrucciones para Ejecutar el Servidor
- Instalar las dependencias requeridas utilizando pip install -r requirements.txt.

- Configurar las variables de entorno (.env) con los parámetros HOST y PORT.
*Ejemplo*:

> HOST= (vacio para escuchar todas las direcciones disponibles)
PORT=5000

> IPv4 loopback
HOST=127.0.0.1

> IPv6 loopback
HOST=::1

> Escuchar en todas las IPv6
HOST=::

- Iniciar el servidor ejecutando el archivo principal (server.py).

- Para detener el servidor de forma segura, ingresar el comando exit en la consola.

### Instrucciones para Ejecutar el Cliente

- Ejecutar el archivo client.py mediante linea de comandos, especificando la dirección IP del servidor, el puerto y la ruta del archivo .txt a convertir. Ejemplo:

> python client.py --ip 127.0.0.1 --port 5000 --file_path prueba.txt
> python client.py --ip 2001:0db8:85a3:0000:0000:8a2e:0370:7334 --port 5000 --file_path prueba.txt
