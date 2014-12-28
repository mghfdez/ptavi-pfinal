#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
IGNACIO ARRANZ ÁGUEDA - ISAM - PTAVI - PRACTICA FINAL
"""

import SocketServer
import sys
import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


metodos = ("INVITE", "BYE", "ACK")

def log_status (Estado):
    fich = open("LOG_SERVER", "a")
    fich.write(time.strftime('%Y%m%d%H%M%S '))
    fich.write(Estado+"\r")

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
                    print "Mensaje de entrada " + line
                    line = line.split()

                    if ("sip:" in line[1][:4]) and \
                            ("@" in line[1]) and line[2] == 'SIP/2.0':

                        line[1] = line[1].split(":")
                        METODO = line[0]

                        if METODO not in metodos:
                            self.wfile.write("SIP/2.0 405 Method \
                                Not Allowed\r\n\r\n")
                        else:
                            if METODO == "INVITE" and line[2] == "SIP/2.0":

                                Answer = "SIP/2.0 100 Trying\r\n\r\n" + \
                                    "SIP/2.0 180 Ringing\r\n\r\n" + \
                                    "SIP/2.0 200 OK\r\n\r\n"

                                self.wfile.write(Answer)
                            elif METODO == "ACK":
                                print "Comienza la transmision........."
                                Streaming = './mp32rtp -i 127.0.0.1 -p \
                                    23032 <' + FILE
                                os.system(Streaming)
                                print "Fin de la emision"
                            elif METODO == "BYE":
                                self.wfile.write("SIP/2.0 200 OK\r\n\r\n")
                    else:
                        self.wfile.write("SIP/2.0 400 Bad Request\r\n\r\n")
#============================ PROGRAMA PRINCIPAL ===========================
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
    LOG_SERVER = myHandler.elementos["log_path"]

    UASERVER_IP = myHandler.elementos["uaserver_ip"]
    UASERVER_PORT = int(myHandler.elementos["uaserver_puerto"])

    # Creamos servidor de eco y escuchamos
    serv = SocketServer.UDPServer(("", UASERVER_PORT), EchoHandler)
    print "Listening..."
    serv.serve_forever()
