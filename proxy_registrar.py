#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - Servidor Proxy-Registrar - Miguel Angel Fernandez Sanchez
"""
Clase (y programa principal) para un servidor SIP-proxy_registrar
en UDP
"""


import SocketServer
import socket
import sys
import os
import time
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class SIPConfigHandler(ContentHandler):
    """
    Clase para manejar fichero de configuracion para Serv. Proxy/Regist. SIP
    """
    def __init__(self):
        """
        Constructor
        """
        
        self.dicc_config = {
                            'server': ['name', 'ip', 'puerto'],
                            'database': ['path', 'passwdpath'],
                            'log': ['path'],
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
                if atr_name == 'server_ip':
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

def write_log(fichero, evento):
    fich = open(fichero, 'a')
    datime = time.strftime("%Y%m%d%Y%H%M%S", time.gmtime())
    linea = str(datime) + ' ' + evento + '\r\n'
    fich.write(linea)
    fich.close()

def formar_evento(tipo, datos, ip, puerto):
    """ 
    Forma el evento que se escribirá en el fichero de log
    """
    accion = tipo
    if tipo == 'envio':
        accion = "Sent to " + ip + ':' + puerto + " "
    elif tipo == 'recepcion':
        accion = "Received from " + ip + ':' + puerto + " "
    elif tipo == 'error':
        accion = 'Error: '

    #Cambiamos los saltos de línea y lineas en blanco por espacios.
    datos = datos.split()
    datos = " ".join(datos)
    frase = accion + datos
    return frase

def check_request(lista):
    # Comprueba si la petición recibida esta bien formada
    lista_ok = ['SIP/2.0', 'sip', 2]
    lista_check = ['', '', '']
    try:
        # Relleno lista y comparo para saber si los datos son los esperados
        lista_check[0] = lista[2]
        user = lista[1].split(":")
        lista_check[1] = user[0]
        user_data = user[1].split('@')
        lista_check[2] = len(user_data)
        return lista_check == lista_ok
    except IndexError:
        print "500 Server Internal Error"
        return 0


# Recopilamos datos de entrada y comprobamos errores
usage = "Usage: python proxy_registrar.py config"
server_data = sys.argv
mi_serv = ""

if len(server_data) != 2:
    print usage
    raise SystemExit
else:
    fichero = server_data[1]
    if not os.path.exists(fichero):
        print 'No existe fichero XML'
        print usage
        raise SystemExit
    else:
        mi_serv = SIPConfigLocal(fichero)

VER = "SIP/2.0"
datos_sesion = mi_serv.get_tags()
log_path = str(datos_sesion['log_path'])
log_fich = open(log_path, 'w')
log_fich.close()
evento = formar_evento('Listening','...','','')
write_log(log_path, evento)
IP = datos_sesion['server_ip']
PORT = int(datos_sesion['server_puerto'])
DICC_CLIENT = {}
name_database = datos_sesion['database_path']


class SIPRegisterHandler(SocketServer.DatagramRequestHandler):
    """
    Clase Registrar-SIP
    """
    def clean_dic(self):
        """
        Limpia el diccionario de usuarios con plazo expirado
        """
        time_now = time.time()
        for user in DICC_CLIENT.keys():
            if DICC_CLIENT[user][1] < time_now:
                print "BORRADO cliente " + user + " (Plazo expirado)"
                del DICC_CLIENT[user]

    def register2file(self):
        """
        Imprime con formato "User \t IP \t Expires"
        el diccionario de clientes en un fichero.
        """
        fich = open(name_database, 'w')
        fich.write("User \t IP \t Expires\r\n")
        for user in DICC_CLIENT.keys():
            host = DICC_CLIENT[user][0]
            seg = DICC_CLIENT[user][1]
            str_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(seg))
            texto = user + '\t' + host + '\t' + str_time + '\r\n'
            fich.write(texto)
        fich.close()

    def handle(self):
        """
        Maneja peticiones SIP del cliente: si la petición es correcta,
        guarda los datos (en un diccionario y en un fichero) y responde un
        mensaje de confirmación al cliente. Si no, envía un mensaje de error.
        """
        while 1:
            cadena = self.rfile.read()
            if cadena != "":
                list_words = cadena.split()
                if list_words[0] == 'REGISTER':
                    self.clean_dic()
                    correo = list_words[1]
                    correo = correo.split(":")[1]
                    try:
                        exp_time = int(list_words[4])
                    except ValueError:
                        self.wfile.write("SIP/2.0 400 BAD REQUEST\r\n\r\n")
                        break
                    exp_sec = exp_time + time.time()
                    dir_ip = self.client_address[0]
                    DICC_CLIENT[correo] = [dir_ip, exp_sec]
                    self.register2file()
                    print "AÑADIDO cliente " + correo
                    print "Expira en: " + str(exp_time) + " seg.\r\n"
                    self.wfile.write("SIP/2.0 200 OK\r\n\r\n")
                    if exp_time == 0:  # Damos de baja al cliente
                        print "DADO DE BAJA cliente " + correo + '\n'
                        del DICC_CLIENT[correo]
                        self.register2file()
                        self.wfile.write("SIP/2.0 200 OK\r\n\r\n")
                elif list_words[0] == 'INVITE':
                    print " "
                elif list_words[0] == 'ACK':
                    print " "
                elif list_words[0] == 'BYE':
                    print " "       
                else:
                    self.clean_dic()
                    self.wfile.write("SIP/2.0 400 BAD REQUEST\r\n\r\n")
            else:
                break

if __name__ == "__main__":
    # Creamos servidor SIP y escuchamos
    serv = SocketServer.UDPServer((IP, PORT), SIPRegisterHandler)
    print "Lanzando servidor UDP de SIP...\r\n"
    serv.serve_forever()
