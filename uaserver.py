#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import SocketServer
import sys
import time
import uaclient
import os

from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class EchoHandler(SocketServer.DatagramRequestHandler):
    """
    Echo server class
    """
    listaRTP = []

    def handle(self):

        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()
            text = line.split()
            if not text:
                break

            doIt = False
            if text[2] == "SIP/2.0":
                userSip = text[1].split(":")
                if len(userSip) == 2:
                    sip = userSip[0]
                    if (sip == "sip"):
                            method = text[0]
                            doIt = True
                    else:
                        print "El cliente nos manda " + line
                        message = "SIP/2.0 400 Bad Request" + '\r\n\r\n'
                        self.wfile.write(message)
                else:
                    print "El cliente nos manda " + line
                    message = "SIP/2.0 400 Bad Request" + '\r\n\r\n'
                    self.wfile.write(message)
            else:
                print "El cliente nos manda " + line
                message = "SIP/2.0 400 Bad Request" + '\r\n\r\n'
                self.wfile.write(message)

            if doIt:
                if method == "INVITE":
                    receptor_portRTP = text[11]
                    receptor_ipRTP = text[7]
                    self.listaRTP.append(receptor_portRTP)
                    self.listaRTP.append(receptor_ipRTP)
                    print "El cliente nos manda " + line
                    trying = "SIP/2.0 100 Trying" + '\r\n\r\n'
                    ringing = "SIP/2.0 180 Ring" + '\r\n\r\n'
                    acept = "SIP/2.0 200 OK" + '\r\n\r\n'
                    sdp = '\r\n' + "Content-Type: application/sdp" + '\r\n\r\n'
                    sdp = sdp + "v=0" + '\r\no=' + username + " " + serverIp
                    sdp = sdp + '\r\ns=misesion' + '\r\nt=0' + '\r\nm=audio '
                    sdp = sdp + rtpPort + " RTP" + '\r\n'
                    message = trying + ringing + acept + sdp
                    self.wfile.write(message)
                elif method == "ACK":
                    print "El cliente nos manda " + line
                    aEjecutar = './mp32rtp -i ' + self.listaRTP[1] + ' -p '
                    aEjecutar = aEjecutar + self.listaRTP[0] + ' < ' + fichRtp
                    print "Vamos a ejecutar", aEjecutar
                    os.system(aEjecutar)
                elif method == "BYE":
                    print "El cliente nos manda " + line
                    message = "SIP/2.0 200 OK" + '\r\n\r\n'
                    self.wfile.write(message)
                else:
                    message = "SIP/2.0 405 Method Not Allowed" + '\r\n\r\n'
                    self.wfile.write(message)
            if not line:
                break

if __name__ == "__main__":

    if len(sys.argv) != 2:
        sys.exit("Usage: python uaserver.py config")

    parser = make_parser()
    cHandler = uaclient.UserXML()  # llamo a la clase userxml de cliente
    parser.setContentHandler(cHandler)
    try:
        fichXML = sys.argv[1]
        parser.parse(open(fichXML))
    except:
        sys.exit("ERROR " + sys.argv[1] + " NOT FOUND")

    lista = cHandler.get_listas()
    listaAtrb = cHandler.get_Atributos()
    listaEtq = cHandler.get_Etiquetas()

    username = listaAtrb[0]
    password = listaAtrb[1]
    serverPort = listaAtrb[2]
    serverIp = listaAtrb[3]
    rtpPort = listaAtrb[4]
    proxyPort = listaAtrb[5]
    proxyIp = listaAtrb[6]
    fichLog = listaAtrb[7]
    fichRtp = listaAtrb[8]

    try:
        os.stat(fichRtp)
    except OSError:
        sys.exit("Error: Don't exist file")

    serv = SocketServer.UDPServer((serverIp, int(serverPort)), EchoHandler)
    print 'Listening...'
    serv.serve_forever()
