#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
IGNACIO ARRANZ ÁGUEDA - ISAM - PTAVI - PRACTICA FINAL - UASERVER
"""

import SocketServer
import sys
import os
import time
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


metodos = ("INVITE", "BYE", "ACK")
port_rtp_dic = {}


def log_status(Estado):
    fich = open("LOG_SERVER.txt", "a")
    fich.write(time.strftime('%Y%m%d%H%M%S '))
    fich.write(Estado+"\r")


# ================================ OBJETOS =================================
class XMLHandler(ContentHandler):
    """
    Extrae los campos del fichero .xml
    """
    def __init__(self):
        # Declaramos el diccionario
        self.elementos = {}
        self.tags = ["account", "uaserver", "rtpaudio", "regproxy", "log", "audio"]
        self.atributos = {
            "account": ["username", "passwd"],
            "uaserver": ["ip", "puerto"],
            "rtpaudio": ["puerto"],
            "regproxy": ["ip", "puerto"],
            "log": ["path"],
            "audio": ["path"]
        }

    def get_tags(self):
        return self.elementos

    def startElement(self, name, attrs):
        if name in self.tags:
            for atributo in self.atributos[name]:
                self.elementos[name + "_" + atributo] = attrs.get(atributo, "")


class EchoHandler(SocketServer.DatagramRequestHandler):
    def handle(self):
        """
        Server SIP
        """
        # Escribe dirección y puerto del cliente.
        client_address = self.client_address[0]
        client_port = int(self.client_address[1])

        while 1:
            # Leyendo línea a línea lo que nos envía el cliente.
            line = self.rfile.read()
            if not line:
                break
            else:
                if "\r\n\r\n" in line:
                    print
                    print "MENSAJE DE ENTRADA"
                    print "=================="
                    print line
                    line = line.split()
                    print line

                    if ("sip:" in line[1][:4]) and \
                            ("@" in line[1]) and line[2] == 'SIP/2.0':

                        line[1] = line[1].split(":")
                        METODO = line[0]

                        if METODO not in metodos:
                            self.wfile.write("SIP/2.0 405 Method \
                                Not Allowed\r\n\r\n")
                        else:
# =============================== INVITE ==================================

                            if METODO == "INVITE" and line[2] == "SIP/2.0":
                                Inv_log = "Received INVITE from " \
                                    + str(line[1]) + ":" + "200 OK [...]"
                                log_status(Inv_log)

                                # Guardamos en un diccionario el usuario y
                                # puerto que entra
                                ip_destino =line[1][1].split("@")[1]
                                port_rtp_dic[ip_destino] = line[-2]

                                print "line[1][1] VALE ¿¿?¿¿?¿?¿?¿?¿¿", line[1][1]
                                # Se forma el SPD
                                NAME = line[6].split("=")[1]
                                RTP_PORT = myHandler.elementos["rtpaudio_puerto"]

                                SDP = "v=0\r\n" + "o=" + NAME + "\r\n" \
                                    + "s=SesionSIP\r\n" + "m=audio " \
                                    + str(RTP_PORT) + " RTP"

                                LINE = METODO + " sip:" + NAME + " SIP/2.0\r\n"
                                LINE += "Content-Type: application/sdp\r\n\r\n"
                                LINE += str(SDP)

                                Answer = "SIP/2.0 100 Trying\r\n\r\n" + \
                                    "SIP/2.0 180 Ringing\r\n\r\n" + \
                                    "SIP/2.0 200 OK\r\n\r\n" + SDP

                                # Formado el SDP se contesta
                                self.wfile.write(Answer)

# =============================== ACK ====================================
                            elif METODO == "ACK":
                                # LOG:
                                Ack_log = "Received ACK from " + str(line[1][1]) \
                                    + ":" + "200 OK [...]"
                                log_status(Ack_log)

                                ip_destino = line[1][1].split("@")[1]

                                # RTP
                                print "Comienza la transmision........."
                                Streaming = './mp32rtp -i ' + ip_destino + \
                                    " -p " + port_rtp_dic[ip_destino]
                                Streaming += " < " + FILE
                                os.system(Streaming)
                                print "Fin de la emision"

                                # LOG:
                                rtp_log = "Send RTP to " + str(line[1][1]) + \
                                    ":" + "200 OK [...]"
                                log_status(rtp_log)

# =============================== BYE ===========================
                            elif METODO == "BYE":

                                print
                                print
                                print "A veeeeer, line[1][1] vale: ", line[1][1]

                                Bye_log = "Received BYE from " + \
                                    client_address + ":" + "200 OK [...]"
                                log_status(Bye_log)

                                self.wfile.write("SIP/2.0 200 OK\r\n\r\n")
                    else:
                        self.wfile.write("SIP/2.0 400 Bad Request\r\n\r\n")

#============================ PROGRAMA PRINCIPAL ==================
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
    #print myHandler.get_tags()

    # Extraer campos del diccionario
    LOG_SERVER = myHandler.elementos["log_path"]

    FILE = myHandler.elementos["audio_path"]

    UASERVER_IP = myHandler.elementos["uaserver_ip"]
    UASERVER_PORT = int(myHandler.elementos["uaserver_puerto"])
    #print "Puerto al que se ata", UASERVER_PORT

    # Creamos servidor de eco y escuchamos
    serv = SocketServer.UDPServer(("", UASERVER_PORT), EchoHandler)
    print "Listening..."
    serv.serve_forever()
