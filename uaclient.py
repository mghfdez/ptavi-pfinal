#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
IGNACIO ARRANZ ÁGUEDA - ISAM - PTAVI - PRACTICA FINAL - USERAGENG
"""

import time
import socket
import sys
import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


metodos = ("REGISTER", "INVITE", "BYE", "ACK")


# ================================ OBJETOS =================================
class XMLHandler(ContentHandler):
    def __init__(self):
        # Declaramos el diccionario
        self.elementos = {}
        self.tags = ["account", "uaserver", "rtpaudio",
                                "regproxy", "log", "audio"]
        self.atributos = {
            "account": ["username", "passwd"],
            "uaserver": ["ip", "puerto"],
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
# =============================== FUNCIONES ===================================


def log_status(Estado):
    fich = open("LOG_CLIENT.txt", "a")
    fich.write(time.strftime('%Y%m%d%H%M%S '))
    fich.write(Estado+"\r")


def saca_puerto_rtp(data):
    rtp_split = data.split("\r\n")[3]
    rtp_port = rtp_split.split(" ")[1]
    return rtp_port

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

# Extraer campos del diccionario
# ================================================
# UASERVER del USERAGENT, no del proxy
UASERVER_IP = myHandler.elementos["uaserver_ip"]
UASERVER_PORT = myHandler.elementos["uaserver_puerto"]
NAME = myHandler.elementos["account_username"]
PASS = myHandler.elementos["account_passwd"]
# Puerto RTP al que se le enviará el tráfico RTP
MY_RTP_PORT = myHandler.elementos["rtpaudio_puerto"]
LOG_CLIENT = myHandler.elementos["log_path"]
# IP y PUERTO del proxy-registral
PROXY_IP = myHandler.elementos["regproxy_ip"]
PROXY_PORT = int(myHandler.elementos["regproxy_puerto"])
# Parámetro que se pasa por línea de comandos:
OPCION = sys.argv[3]

if len(sys.argv) == 4:
    METODO = sys.argv[2]
    if METODO == "REGISTER" and len(sys.argv) == 4:
        LINE = METODO + " sip:" + NAME + "@" + UASERVER_IP + ":" \
            + UASERVER_PORT + " SIP/2.0\r\n"
        LINE = LINE + "Expires: " + OPCION + "\r\n\r\n"
        # LOG -- REGISTER ----
        Start_log = "Starting..."
        # -----------------------
        log_status(Start_log)
    elif METODO == "INVITE" and len(sys.argv) == 4:
        SDP = "v=0\r\n" + "o=" + NAME + "@" + UASERVER_IP \
            + " " + UASERVER_IP + "\r\n" + "s=SesionSIP\r\n" \
            + "m=audio " + str(MY_RTP_PORT) + " RTP"
        LINE = METODO + " sip:" + OPCION + " SIP/2.0\r\n"
        LINE += "Content-Type: application/sdp\r\n\r\n"
        LINE += str(SDP)
    elif METODO == "BYE" and len(sys.argv) == 4:
        LINE = METODO + " sip:" + OPCION + " SIP/2.0\r\n\r\n"
    else:
        LINE = METODO + " sip:" + UASERVER_IP \
            + str(UASERVER_PORT) + " SIP/2.0\r\n\r\n"

# Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
my_socket.connect((UASERVER_IP, PROXY_PORT))

# Envio de informacion
print "Enviando: " + LINE
my_socket.send(LINE)
# LOG -------------
LINE = LINE.replace("\r\n", " ")
Sent_log = "Sent to " + str(PROXY_IP) + ":" \
    + str(PROXY_PORT) + " " + LINE
log_status(Sent_log)
# -----------------
try:
    data = my_socket.recv(1024)
    print
    print 'MENSAJE DE ENTRADA'
    print "=================="
    print data
    #LOG -- data --------------------------------
    mensaje_entrada = data.replace("\r\n\r\n", " ")
    Recv_log = "Received from " + str(PROXY_IP) + ":" + str(PROXY_PORT) \
        + " " + mensaje_entrada
    Recv_log = Recv_log.replace("\r\n", " ")
    log_status(Recv_log)
    # -------------------------------------------
except socket.error:
    fecha = time.strftime('%Y%m%d%h%M%S', time.gmtime(time.time()))
    print "Error: No server listening at", UASERVER_IP, "port", PROXY_PORT
    sys.exit()
    # LOG -- error -----------------------------------
    Recv_log_error = "Error: No server listening at" \
        + UASERVER_IP + "port" + PROXY_PORT
    log_status(Recv_log)
    # ------------------------------------------------
data = data.split("\r\n\r\n")
if data[0] == "SIP/2.0 100 Trying" and data[1] == "SIP/2.0 180 Ringing":
    if data[2] == "SIP/2.0 200 OK\r\nContent-Type: application/sdp":
        # Se envia ACK
        METODO = "ACK"
        LINE = METODO + " sip:" + OPCION + " SIP/2.0\r\n\r\n"
        # Envio de informacion
        print "Enviando Confirmacion: " + LINE
        my_socket.send(LINE)

        # LOG --- ACK ---------
        Ack_log = "Sent ACK to " + str(PROXY_IP) + ":" \
            + str(PROXY_PORT) + " " + LINE.replace("\r\n\r\n", " ")
        log_status(Ack_log)
        # ---------------------

        data[3] = data[3].split("\r\n")
        OPCION = data[3][1].split(" ")[1]

        # Puerto de envío de tráfico RTP:
        rtp_port = data[3][3].split(" ")[1]

        # LOG --RTP--------------
        Rtp_log = "Sent RTP to: " + str(OPCION) + ":" + str(rtp_port)
        log_status(Rtp_log)
        # ----------------------

        # OPCIONAL --------Ponemos en segundo plano el cvlc:
        audio = "cvlc rtp://" + str(UASERVER_IP) + ":" + MY_RTP_PORT + "&"
        print audio
        os.system(audio)
        # ---------------------------------------------------
        print "Comienza la transmision........."
        Streaming = './mp32rtp -i ' + OPCION + " -p " + rtp_port
        Streaming += " < " + myHandler.elementos["audio_path"]
        os.system(Streaming)
        print "Fin de la emision"
# Cerramos todo
my_socket.close()
