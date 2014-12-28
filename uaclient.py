#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
IGNACIO ARRANZ ÁGUEDA - ISAM - PTAVI - PRACTICA FINAL
"""

import time
import socket
import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler



metodos = ("REGISTER", "INVITE", "BYE", "ACK")

# ================================ OBJETOS =================================
class XMLHandler(ContentHandler):
    def __init__(self):
        # Declaramos el diccionario
        self.elementos = {}
        self.tags = ["account", "uaserver", "rtpaudio", "regproxy", "log", "audio"]
        self.atributos = {
            "account": ["username", "passwd"],
            "uaserver": ["ip","puerto"],
            "rtpaudio": ["puerto"],
            "regproxy": ["ip", "puerto"],
            "log": ["path"],
            "audio": ["path"]
        }

    def get_tags(self):
    # Devuelve una lista con etiquetas, atributos y contenidos encontrados
        return self.elementos
    
    def startElement(self, name, attrs):
        if name in self.tags:
            for atributo in self.atributos[name]:
                self.elementos[name + '_' + atributo] = attrs.get(atributo, "")  
# =============================== FUNCIONES ====================================
def log_status (Estado):
    fich = open("LOG_CLIENT", "a")
    fich.write(time.strftime('%Y%m%d%H%M%S '))
    fich.write(Estado+"\r")





# ========================== PROGRAMA PRINCIPAL ===============================
if __name__ == "__main__":
    # ======= OBTENCIÓN DE VALORES DEL FICHERO .xml =========
    try:
        fich = sys.argv[1]
    except IndexError:
        print "Usage: python file.py file.xml"
    parser = make_parser()
    myHandler = XMLHandler()
    parser.setContentHandler(myHandler)
    parser.parse(open(fich))
    print myHandler.get_tags()



# Extraer campos del diccionario
# ===============================

# UASERVER del USERAGENT, no del proxy
UASERVER_IP = myHandler.elementos["uaserver_ip"]
UASERVER_PORT = myHandler.elementos["uaserver_puerto"]

# Puerto RTP al que se le enviará el tráfico
RTP_PORT = myHandler.elementos["rtpaudio_puerto"]

NAME = myHandler.elementos["account_username"]
LOG_CLIENT = myHandler.elementos["log_path"]

# IP y PUERTO del proxy-registral
PROXY_IP = myHandler.elementos["regproxy_ip"]
PROXY_PORT = int(myHandler.elementos["regproxy_puerto"])

OPCION = sys.argv[3]

if len(sys.argv) == 4:
    # METODO
    METODO = sys.argv[2]
    print METODO

    if METODO == "REGISTER" and len(sys.argv) == 4:
        LINE = METODO + " sip:" + NAME + "@" + UASERVER_IP + ":" \
                + UASERVER_PORT +  " SIP/2.0\r\n"
        LINE = LINE + "Expires: " + OPCION + "\r\n\r\n"

    elif METODO == "INVITE" or METODO == "BYE":
        SDP = "v=0\r\n" + "o=" + NAME + "@" + UASERVER_IP + "\r\n" \
                + "s=SesionSIP\r\n" + "m=audio " + str(RTP_PORT) + " RTP"

        LINE = METODO + " sip:" + OPCION + "@" + UASERVER_IP + " SIP/2.0\r\n"
        LINE += "Content-Type: application/sdp\r\n\r\n"
        LINE += str(SDP)

    else:
        print "Usage: python uaclient.py config method option"

# Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
my_socket.connect((UASERVER_IP, PROXY_PORT))

Start_log = "Starting..."
log_status(Start_log)

# Envio de informacion
print "Enviando: " + LINE
my_socket.send(LINE + '\r\n')

# Log
Sent_log = "Sent to " + str(UASERVER_IP[0]) + ":" \
            + str(UASERVER_PORT) + " " + str(LINE.split("\r\n")[0])
log_status(Sent_log)


try:
    data = my_socket.recv(1024)
    print 'Recibido -- ', data
    #Log
    Answers = "200 OK [...]"
    Recv_log = "Received from " + str(NAME) + ":" + str(UASERVER_PORT) \
                + ":" + Answers
    log_status(Recv_log)
except socket.error:
    fecha = time.strftime('%Y%m%d%h%M%S', time.gmtime(time.time()))
    print "Error: No server listening at", UASERVER_IP, "port", PROXY_PORT
    sys.exit()


data = data.split("\r\n\r\n")

if data[0] == "SIP/2.0 100 Trying" and data[1] == "SIP/2.0 180 Ringing":
    if data[2] == "SIP/2.0 200 OK":
        # Se envia ACK
        METODO = "ACK"
        LINE = METODO + " sip:" + NAME + "@" + UASERVER_IP + " SIP/2.0\r\n"
        # Envio de informacion
        print "Enviando Confirmacion: " + LINE
        my_socket.send(LINE + '\r\n')

# Cerramos todo
my_socket.close()
