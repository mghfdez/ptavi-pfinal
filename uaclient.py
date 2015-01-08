#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import socket
import sys
import time
import os

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

# Clase para leer el fichero xml

class UserXML(ContentHandler):

    def __init__(self):

        self.etiquetas = {"account": ["username", "passwd"],
                        "uaserver": ["ip", "puerto"],
                        "rtpaudio": ["puerto"],
                        "regproxy": ["ip", "puerto"],
                        "log": ["path"],
                        "audio": ["path"]}
        self.list = []
        self.listEtiquetas = []
        self.listAtributos = []

    def startElement(self, name, attrs):
        if name in self.etiquetas:
            dic = {}
            dic["__name__"] = name  # añadimos el nombre de la etiqueta al dicc
            # buscamos atributo en self.etiquetas
            for atributo in self.etiquetas[name]:
                dic[atributo] = attrs.get(atributo, "")
            self.list.append(dic)

    def get_tags(self):
        return self.list

    def get_listas(self):

        valor = ""
        valorAtributo = ""

        for elemento in self.list:
            diccionario = elemento  # Cada elemento contiene un diccionario
            for clave in diccionario.keys():
                if clave != "__name__":
                    valorAtributo = diccionario[clave]
                    self.listAtributos.append(valorAtributo)
                else:
                    etiqueta = diccionario[clave]
            self.listEtiquetas.append(etiqueta)

    def get_Atributos(self):
        return self.listAtributos

    def get_Etiquetas(self):
        return self.listEtiquetas

#imprime por pantalla, escribe en el log y envia el mensaje
def enviar_msg(text, fich):
    print "Enviando: " + text
    line = "Send to: " + proxyIp + ":" + str(proxyPort) + ": " + text
    escribir_log(line, fich)
    my_socket.send(text + '\r\n\r\n')

#recibe en el buffer los mensajes con los codigos de respuesta
def rcv_data(fich):
    try:
        dataRcv = my_socket.recv(1024)
    except:
        error_server(fich)
    print 'Recibido -- ', dataRcv
    textLog = "Received from IP:PORT: " + dataRcv
    escribir_log(textLog, fich)
    return dataRcv

#termina la ejcución del cliente
def fin_socket(bye, fich):
    print "Terminando socket..."
    if (bye == True):
        text = "Finishing."
        escribir_log(text, fich)
    my_socket.close()
    print "Fin."

#excepcion por introducir parametros incorrectos
def error_usage():
    sys.exit("Usage: python uaclient.py config metodo opcion")

#no encuentra el servidor 
def error_server(fich):
    text = "Error: no server listening at " + proxyIp
    text = text + " port " + str(proxyPort)
    escribir_log(text, fich)
    sys.exit(text)

#escribe en el log
def escribir_log(text, fich):
    fich = open(fich, 'a')  # 'a' es para escribir al final, no 'w'
    tiempo = time.strftime('%Y­%m­%d%H%M%S', time.gmtime(time.time()))
    textFich = tiempo + " " + str(text) + '\r\n'
    fich.write(textFich)
    fich.close()

if __name__ == "__main__":
    #el ack no se pasa como parametro
    METHODS = ['REGISTER', 'INVITE', 'BYE']
    DATA = ['200', '100', '180']

    # Cliente UDP simple.
    if len(sys.argv) != 4:
        error_usage()

    parser = make_parser()
    cHandler = UserXML()
    parser.setContentHandler(cHandler)
    try:
        fichXML = sys.argv[1]
        parser.parse(open(fichXML))
    except:
        sys.exit("ERROR " + sys.argv[1] + " NOT FOUND")

    lista = cHandler.get_listas()
    listaAtrb = cHandler.get_Atributos()
    listaEtq = cHandler.get_Etiquetas()
    # Sacamos las variables del XML
    username = listaAtrb[0]
    password = listaAtrb[1]
    serverPort = listaAtrb[2]
    serverIp = listaAtrb[3]
    #if "ip" in listaEtq:
    #    if (serverIp == 'localhost'):
    #        serverIp = "127.0.0.1"
    #else:
    #    serverIp = "127.0.0.1"
    rtpPort = listaAtrb[4]
    proxyPort = listaAtrb[5]
    proxyIp = listaAtrb[6]
    #if proxyIp == 'localhost':
    #    proxyIp = "127.0.0.1"
    fichLog = listaAtrb[7]
    fichRtp = listaAtrb[8]

    # Iniciamos el cliente
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((proxyIp, int(proxyPort)))
    line = "Starting..."
    escribir_log(line, fichLog)

    # Comprobamos los métodos que tenemos
    method = sys.argv[2]
    if method not in METHODS:
        error_usage()
    else:
        if method == "REGISTER":
            expire = int(sys.argv[3])
            line = method + " sip:" + username + ":" + serverPort + " SIP/2.0"
            line = line + '\r\n' + "Expires: " + str(expire)
            enviar_msg(line, fichLog)
            dataRcv = rcv_data(fichLog)
        else:
            receptor = sys.argv[3]
            if method == "INVITE":
                line = method + " sip:" + receptor + " SIP/2.0" + '\r\n'
                line = line + "Content-Type: application/sdp" + '\r\n\r\n'
                line = line + "v=0" + '\r\n' + "o=" + username + " " + serverIp
                line = line + '\r\n' + "s=misesion" + '\r\n' + "t=0" + '\r\n'
                line = line + "m=audio " + rtpPort + " RTP"
                enviar_msg(line, fichLog)

                # Recibo datos
                dataRcv = rcv_data(fichLog)
                if len(dataRcv.split()) == 19:
                    trying = dataRcv.split()[1]
                    ringing = dataRcv.split()[4]
                    accept = dataRcv.split()[7]
                    receptor_rptIp = dataRcv.split()[13]
                    receptor_rtpPort = dataRcv.split()[17]
                    if (trying and ringing and accept) in DATA:
                        method = "ACK"
                        line = method + " sip:" + receptor + " SIP/2.0"
                        enviar_msg(line, fichLog)
                        aEjecutar = 'mp32rtp -i ' + receptor_rptIp + ' -p '
                        aEjecutar = aEjecutar + receptor_rtpPort + ' < '
                        aEjecutar = aEjecutar + fichRtp
                        print "Vamos a ejecutar", aEjecutar
                        os.system(aEjecutar)
                    esBye = False
                    fin_socket(esBye, fichLog)
            elif method == "BYE":
                line = method + " sip:" + receptor + " SIP/2.0"
                enviar_msg(line, fichLog)
                # Recibo datos
                dataRcv = rcv_data(fichLog)
                textLog = "Received from IP:PORT: " + dataRcv
                escribir_log(textLog, fichLog)
                esBye = True
                fin_socket(esBye, fichLog)





