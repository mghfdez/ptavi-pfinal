#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import socket
import sys
import time
import SocketServer
import os
import uaclient

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

# Importar la clase Para leer el xml


class ProxyXML(ContentHandler):

    def __init__(self):

        self.etiquetas = {"server": ["name", "ip", "puerto"],
                        "database": ["path"],
                        "log": ["path"]}
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


class SIPRegisterHandler(SocketServer.DatagramRequestHandler):
    """
    Echo server class
    """
    dic = {}

    def handle(self):
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()
            resend_line = line
            text = line.split()
            if not text:
                break

            method = text[0]
            user = text[1].split(":")
            userName = user[1]
            if method in METHODS:
                if method == "REGISTER":
                    userPort = int(user[2])
                    expire = int(text[4])
                    timeExpire = time.time() + expire
                    print "El cliente nos manda " + line
                    # ver si hay algun cliente caducado
                    borrado = False
                    delList = []
                    if len(self.dic) != 0:
                        for element in self.dic:
                            if (time.time() >= self.dic[element][2]):
                                delList.append(element)
                        for direccion in delList:
                            del self.dic[direccion]
                        self.register2file()
                        delList = []
                    if expire == 0:
                        for name in self.dic:
                            if userName == name:
                                # Borrar del diccionario al usuario
                                borrado = True
                                delList.append(name)
                        for element in delList:
                            del self.dic[element]
                        self.register2file()
                        delList = []
                        if borrado == True:
                            message = "SIP/2.0 200 OK"
                            self.wfile.write(message + "\r\n\r\n")
                            textLog = "Send to: " + proxyIp + ":"
                            textLog = textLog + str(proxyPort) + ": " + message
                            uaclient.escribir_log(textLog, fichLog)
                        else:
                            message = "SIP/2.0 410 Gone"
                            self.wfile.write(message + "\r\n\r\n")
                            textLog = "Send to: " + proxyIp + ":"
                            textLog = textLog + str(proxyPort) + ": " + message
                            uaclient.escribir_log(textLog, fichLog)
                    else:
                        ip = str(self.client_address[0])
                        self.list = [ip, userPort, timeExpire]
                        self.dic[userName] = self.list
                        message = "SIP/2.0 200 OK"
                        self.wfile.write(message + "\r\n\r\n")
                        self.register2file()
                        textLog = "Send to: " + proxyIp + ":"
                        textLog = textLog + str(proxyPort) + ": " + message
                        uaclient.escribir_log(textLog, fichLog)
                user_encontrado = False
                if (method == "INVITE") or (method == "BYE") \
                    or (method == "ACK"):
                    # vemos si esta en el diccionario el usuario receptor.
                    for element in self.dic:
                        if userName == element:
                            receptorIp = self.dic[element][0]
                            receptorPort = self.dic[element][1]
                            user_encontrado = True
                    if (user_encontrado == False):
                        line = "SIP/2.0 404 User Not Found"
                        self.wfile.write(line + "\r\n\r\n")
            else:
                message = "SIP/2.0 405 Method Not Allowed" + '\r\n\r\n'
                self.wfile.write(message)
                textLog = "Send to: " + proxyIp + ":"
                textLog = textLog + str(proxyPort) + ": " + message
                uaclient.escribir_log(textLog, fichLog)

            if (user_encontrado == True):
                # Nos conectamos al cliente para reenviarle los datos
                my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                my_socket.connect((receptorIp, int(receptorPort)))
                my_socket.send(resend_line + '\r\n')
                textLog = "Send to: " + proxyIp + ":"
                textLog = textLog + str(proxyPort) + ": " + resend_line
                uaclient.escribir_log(textLog, fichLog)
                if method != "ACK":
                    # Esperamos respuesta del usuario, salvo en el ACK
                    dataRcv = my_socket.recv(1024)
                    print 'Recibido -- ', dataRcv
                    textLog = "Received from IP: " + receptorIp + "PORT: "
                    textLog = textLog + str(receptorPort) + dataRcv
                    uaclient.escribir_log(textLog, fichLog)
                    self.wfile.write(dataRcv)
            if not line:
                break

    def register2file(self):
        fich = open('registered.txt', 'w')
        fich.write('user' + '\t' + 'ip' + '\t' + 'port' + '\t' + 'expire')
        for clave in self.dic:
            userDir = clave
            ip = self.dic[clave][0]
            port = str(self.dic[clave][1])
            timeExp = self.dic[clave][2]
            timeGm = time.gmtime(timeExp)
            expires = time.strftime('%Y­ %m ­%d %H:%M:%S', timeGm)
            text = userDir + '\t' + ip + '\t' + port + '\t' + expires + '\n'
            fich.write(text + '\n')
        fich.close()

if __name__ == "__main__":

    if len(sys.argv) != 2:
        sys.exit("Usage: python proxy_registrar.py config")

    METHODS = ['REGISTER', 'INVITE', 'BYE', 'ACK']
    parser = make_parser()
    cHandler = ProxyXML()
    parser.setContentHandler(cHandler)
    parser.parse(open(sys.argv[1]))
    lista = cHandler.get_listas()
    listaAtrb = cHandler.get_Atributos()
    listaEtq = cHandler.get_Etiquetas()

    proxyPort = listaAtrb[0]
    proxyIp = listaAtrb[2]
    #if proxyIp == 'localhost':
    #    proxyIp = "127.0.0.1"
    nameProxy = listaAtrb[1]
    fichUserReg = listaAtrb[3]
    fichLog = listaAtrb[4]

    proxy = SocketServer.UDPServer(("", int(proxyPort)), SIPRegisterHandler)
    print "Server " + nameProxy + " listening at port " + proxyPort + " ..."
    line = "Starting..."
    uaclient.escribir_log(line, fichLog) #llamamos al metodo que hay en el cliente
    proxy.serve_forever()
