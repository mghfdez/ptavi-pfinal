#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - Miguel Angel Fernandez Sanchez
"""
Programa cliente que abre un socket a un servidor
"""

import socket
import sys
import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

class SIPConfigHandler(ContentHandler):
    """
    Clase para manejar fichero de configuracion para SIP
    """
    def __init__(self):
        """
        Constructor
        """
        
        self.dicc_config = {
                            'account': ['username', 'passwd'],
                            'uaserver': ['ip', 'puerto'],
                            'rtpaudio': ['puerto'],
                            'regproxy': ['ip', 'puerto'],
                            'log': ['path'],
                            'audio': ['path']
                            }

        self.dicc_atrib = {}
        

    def startElement(self, name, attrs):
        """
        Método que se llama cuando se abre una etiqueta
        """

        if name != 'config':
            lista = self.dicc_config[name]
            for campo in lista:
                atr_name = name + '_' + campo
                self.dicc_atrib[atr_name] = attrs.get(campo, "")
                if atr_name == 'uaserver_ip':
                    if self.dicc_atrib[atr_name] == "":
                        self.dicc_atrib[atr_name] = '127.0.0.1'
                

    def get_tags(self):
        """
        Metodo que devuelve el diccionario de elementos
        """
        return self.dicc_atrib

class SIPConfigLocal:
    """
    Clase para gestionar archivos config
    """
    def __init__(self, fich):
        parser = make_parser()
        CHandler = SIPConfigHandler()
        parser.setContentHandler(CHandler)
        self.dicc_datos = {}
        parser.parse(open(fich))
        self.dicc_datos = CHandler.get_tags()

    def __str__(self):
        frase = ""
        for atrib in self.dicc_datos.keys():
            frase = frase + "\r\n" + atrib + '="' + self.dicc_datos[atrib] + '"'
        print frase
    
    def get_tags(self):
        return self.dicc_datos

if __name__ == "__main__":
    """
    Programa principal 
    """
    usage = "Usage: python uaclient.py config method option"
    arg_term = sys.argv
    mi_user = ""
    if len(arg_term) != 4:
        print usage
        raise SystemExit
    else:
        fichero = arg_term[1]
        if not os.path.exists(fichero):
            print 'No existe fichero XML'
            print usage
            raise SystemExit
        else:
            mi_user = SIPConfigLocal(fichero)

    method_list = ['REGISTER', 'INVITE', 'BYE']



    VER = "SIP/2.0"
    datos_sesion = mi_user.get_tags()
    METODO = arg_term[2]
    OPCION = arg_term[3]
    RECEPTOR = datos_sesion['account_username']
    print RECEPTOR
    
    # Comprobamos si el método es conocido
    if METODO not in method_list:
        print usage
        raise SystemExit

    # Dirección IP del servidor.
    IP = datos_sesion['uaserver_ip']
    # Comprobamos si el puerto introducido es correcto
    PORT = datos_sesion['uaserver_port']
    try:
        PORT = int(user_info[1].split(":")[1])
    except ValueError:
        print usage
        raise SystemExit

    # Contenido que vamos a enviar
    LINE = METODO + " sip:" + RECEPTOR + "@" + IP + " " + VER + '\r\n\r\n'

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto

    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((IP, PORT))

    # Comprobamos si hay un servidor escuchando
    try:
        print "Enviando: " + LINE
        my_socket.send(LINE + '\r\n')
        data = my_socket.recv(1024)
        print "Recibido: " + data
    except socket.error:
        print "Error: No server listening at " + IP + " port " + str(PORT)
        raise SystemExit

    if data.split() == lista_ack:
        LINE2 = 'ACK sip:' + RECEPTOR + '@' + IP + " " + VER
        print "Enviando: " + LINE2
        my_socket.send(LINE2 + '\r\n\r\n')
        data2 = my_socket.recv(1024)
        print "Recibido: " + data2
    print "Terminando socket..."

    # Cerramos todo
    my_socket.close()
    print "Fin."
