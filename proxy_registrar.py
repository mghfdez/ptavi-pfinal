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
import uaclient


class SIPConfigHandler(ContentHandler):
    """
    Clase para manejar fichero de configuracion para Serv. Proxy/Regist. SIP
    """
    def __init__(self):
        """
        Constructor
        """

        self.dicc_config = {'server': ['name', 'ip', 'puerto'],
                            'database': ['path', 'passwdpath'],
                            'log': ['path']
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
            frase = frase + "\r\n" + atrib + '="'
            frase += self.dicc_datos[atrib] + '"'
        print frase

    def get_tags(self):
        return self.dicc_datos


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
            if DICC_CLIENT[user][3] < time_now:
                print "BORRADO cliente " + user + " (Plazo expirado)"
                del DICC_CLIENT[user]

    def register2file(self):
        """
        Imprime con formato "User \t IP \t Port \t RegisterDate \t Expires"
        el diccionario de clientes en un fichero.
        """
        fich = open(name_database, 'w')
        first_line = "User \t IP \t Port \t RegisterDate \t Expires\r\n"
        fich.write(first_line)
        for user in DICC_CLIENT.keys():
            host = DICC_CLIENT[user][0]
            port = DICC_CLIENT[user][1]
            reg_date = DICC_CLIENT[user][2]
            seg_exp = DICC_CLIENT[user][3]
            str_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(seg_exp))
            texto = user + '\t' + host + '\t' + str(port)
            texto += '\t' + str(reg_date) + '\t' + str(seg_exp) + '\r\n'
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
                self.clean_dic()
                self.register2file()
                print "Recibido: " + cadena
                dir_ip = self.client_address[0]
                dir_port = self.client_address[1]
                dir_port_s = str(dir_port)
                evento = mi_log.make_event('recepcion', cadena,
                                           dir_ip, dir_port_s)
                list_words = cadena.split()
                if list_words[0] == 'REGISTER':
                    correo = list_words[1]
                    user_dir = correo.split(":")[1]
                    try:
                        exp_time = int(list_words[4])
                        user_port = int(correo.split(":")[2])
                    except ValueError:
                        descrip = "SIP/2.0 400 BAD REQUEST\r\n\r\n"
                        self.wfile.write(descrip)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        break
                    reg_time = time.time()
                    exp_sec = exp_time + reg_time
                    DICC_CLIENT[user_dir] = [dir_ip, user_port,
                                             reg_time, exp_sec]

                    self.register2file()
                    print "AÑADIDO cliente " + user_dir
                    print DICC_CLIENT[user_dir]
                    print "Expira en: " + str(exp_time) + " seg.\r\n"
                    self.wfile.write("SIP/2.0 200 OK\r\n\r\n")
                    evento = mi_log.make_event('envio', cadena,
                                               dir_ip, str(user_port))

                    if exp_time == 0:  # Damos de baja al cliente
                        print "DADO DE BAJA cliente " + user_dir + '\n'
                        del DICC_CLIENT[user_dir]
                        self.register2file()
                        evento = mi_log.make_event('envio', cadena,
                                                   dir_ip, str(user_port))
                        self.wfile.write("SIP/2.0 200 OK\r\n\r\n")

                elif list_words[0] == 'INVITE':
                    lista_cadena = cadena.split('\r\n')
                    peticion = lista_cadena[0].split()
                    dir_dest = peticion[1].split(":")[1]

                    if dir_dest in DICC_CLIENT.keys():
                        IP_DEST = DICC_CLIENT[dir_dest][0]
                        PORT_DEST = DICC_CLIENT[dir_dest][1]
                    else:
                        descrip = "SIP/2.0 404 Not Found\r\n\r\n"
                        self.wfile.write(descrip)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        break

                    for linea_pet in lista_cadena:
                        if linea_pet != "":
                            datos = linea_pet.split('=')
                            if len(datos) == 2:
                                dicc_sdp[datos[0]] = datos[1]

                    emisor = dicc_sdp['o'].split()[0]
                    if emisor not in DICC_CLIENT.keys():
                        descrip = "SIP/2.0 404 Not Found\r\n\r\n"
                        evento = mi_log.make_event('error', descrip, '', '')
                        self.wfile.write(evento)
                        print evento,
                        print "Emisor no registrado"
                        break

                    mi_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    mi_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    mi_socket.connect((IP_DEST, PORT_DEST))
                    try:
                        print 'Reenviando a ' + dir_dest
                        evento = mi_log.make_event('envio', cadena,
                                                   IP_DEST, str(PORT_DEST))
                        mi_socket.send(cadena)
                        data = mi_socket.recv(1024)
                        print "Recibido: " + data
                        evento = mi_log.make_event('recepcion', data,
                                                   IP_DEST, str(PORT_DEST))

                        emisor_ip = DICC_CLIENT[emisor][0]
                        emisor_port = str(DICC_CLIENT[emisor][1])
                        print "Reenviando respuesta a " + str(dicc_sdp['o']),
                        print emisor_port
                        self.wfile.write(data)

                        evento = mi_log.make_event('envio', cadena,
                                                   emisor_ip, emisor_port)
                        print evento
                    except socket.error:
                        descrip = "No server listening at " + IP_DEST
                        descrip = descrip + " port " + str(PORT_DEST)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        self.wfile.write(evento)
                        break

                elif list_words[0] == 'ACK':
                    lista_cadena = cadena.split('\r\n')
                    peticion = lista_cadena[0].split()
                    dir_dest = peticion[1].split(":")[1]
                    IP_DEST = DICC_CLIENT[dir_dest][0]
                    PORT_DEST = DICC_CLIENT[dir_dest][1]

                    mi_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    mi_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    mi_socket.connect((IP_DEST, PORT_DEST))
                    try:
                        print 'Reenviando a ' + dir_dest
                        evento = mi_log.make_event('envio', cadena,
                                                   IP_DEST, str(PORT_DEST))
                        mi_socket.send(cadena)
                    except socket.error:
                        descrip = "No server listening at " + IP_DEST
                        descrip = descrip + " port " + str(PORT_DEST)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        self.wfile.write(evento)
                        break

                elif list_words[0] == 'BYE':
                    lista_cadena = cadena.split('\r\n')
                    peticion = lista_cadena[0].split()
                    dir_dest = peticion[1].split(":")[1]
                    IP_DEST = DICC_CLIENT[dir_dest][0]
                    PORT_DEST = DICC_CLIENT[dir_dest][1]

                    mi_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    mi_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    mi_socket.connect((IP_DEST, PORT_DEST))
                    try:
                        print 'Reenviando a ' + dir_dest
                        evento = mi_log.make_event('envio', cadena,
                                                   IP_DEST, str(PORT_DEST))
                        mi_socket.send(cadena)
                        data = mi_socket.recv(1024)
                        print "Recibido: " + data
                        evento = mi_log.make_event('recepcion', data,
                                                   IP_DEST, str(PORT_DEST))
                        print "Reenviando respuesta..."
                        self.wfile.write(data)
                        evento = mi_log.make_event('envio', data, "", "")
                    except socket.error:
                        descrip = "No server listening at " + IP_DEST
                        descrip = descrip + " port " + str(PORT_DEST)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        self.wfile.write(evento)
                        break
                else:
                    self.clean_dic()
                    self.register2file()
                    descrip = "SIP/2.0 405 METHOD NOT ALLOWED\r\n\r\n"
                    self.wfile.write(descrip)
                    evento = mi_log.make_event('error', descrip, '', '')
            else:
                break

if __name__ == "__main__":
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
    try:
        mi_log = uaclient.LogConfig(log_path)
    except IOError:
        print "Acceso denegado al fichero de log. Revisa el path."
        print usage
        raise SystemExit

    IP = datos_sesion['server_ip']
    PORT = int(datos_sesion['server_puerto'])
    server_name = datos_sesion['server_name']
    DICC_CLIENT = {}
    name_database = datos_sesion['database_path']
    user_dir = ""
    user_port = 0
    dir_dest = ""
    datos_dest = []
    dicc_sdp = {}
    RTP_INFO = {}
    # Creamos servidor SIP y escuchamos
    serv = SocketServer.UDPServer((IP, PORT), SIPRegisterHandler)
    print "Lanzando servidor UDP de SIP...\r\n"
    accion = 'Server ' + server_name + ' listening at port ' + str(PORT)
    evento = mi_log.make_event(accion, '...', '', '')
    print accion + "\r\n"
    serv.serve_forever()
