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
import random


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


def add_proxy_header(cadena, ip, puerto):
    #Añade una cabecera Proxy a la cadena de texto especificada
    cadena += "Via: SIP/2.0/UDP " + ip + ':' + str(puerto) + ';rport;'
    cadena += 'branch=' + str(num_rand) + '\r\n\r\n'
    return cadena


class SIPRegisterHandler(SocketServer.DatagramRequestHandler):
    """
    Clase Registrar-SIP
    """
    def clean_dic(self):
        """
        Limpia el diccionario de usuarios con plazo expirado
        """
        time_now = time.time()
        for user in dicc_client.keys():
            if dicc_client[user][3] < time_now:
                print "BORRADO cliente " + user + " (Plazo expirado)"
                del dicc_client[user]

    def register2file(self):
        """
        Imprime con formato "User \t IP \t Port \t RegisterDate \t Expires"
        el diccionario de clientes en un fichero.
        """
        fich = open(name_database, 'w')
        first_line = "User \t IP \t Port \t RegisterDate \t Expires\r\n"
        fich.write(first_line)
        for user in dicc_client.keys():
            host = dicc_client[user][0]
            port = dicc_client[user][1]
            reg_date = dicc_client[user][2]
            seg_exp = dicc_client[user][3]
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
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        descrip = add_proxy_header(descrip, IP, PORT)
                        self.wfile.write(descrip)
                        evento = mi_log.make_event('envio', descrip,
                                                   dir_ip, dir_port_s)
                        print evento
                        break

                    reg_time = time.time()
                    exp_sec = exp_time + reg_time
                    dicc_client[user_dir] = [dir_ip, user_port,
                                             reg_time, exp_sec]

                    self.register2file()
                    print "AÑADIDO cliente " + user_dir
                    print dicc_client[user_dir]
                    print "Expira en: " + str(exp_time) + " seg.\r\n"
                    resp = "SIP/2.0 200 OK\r\n\r\n"
                    resp = add_proxy_header(resp, IP, PORT)
                    self.wfile.write(resp)
                    evento = mi_log.make_event('envio', resp,
                                               dir_ip, dir_port_s)

                    if exp_time == 0:  # Damos de baja al cliente
                        print "DADO DE BAJA cliente " + user_dir + '\n'
                        del dicc_client[user_dir]
                        self.register2file()
                        resp = "SIP/2.0 200 OK\r\n\r\n"
                        resp = add_proxy_header(resp, IP, PORT)
                        self.wfile.write(resp)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)

                elif list_words[0] == 'INVITE':
                    lista_cadena = cadena.split('\r\n')
                    peticion = lista_cadena[0].split()
                    dir_dest = peticion[1].split(":")[1]

                    if dir_dest in dicc_client.keys():
                        ip_dest = dicc_client[dir_dest][0]
                        port_dest = dicc_client[dir_dest][1]
                    else:
                        descrip = "SIP/2.0 404 User Not Found\r\n\r\n"
                        descrip = add_proxy_header(descrip, IP, PORT)
                        self.wfile.write(descrip)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        evento = mi_log.make_event('envio', descrip,
                                                   dir_ip, dir_port_s)
                        print evento
                        break

                    if not uaclient.check_ip(ip_dest):
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        resp = add_proxy_header(resp, IP, PORT)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)
                        self.wfile.write(resp)
                        print evento
                        break

                    try:
                        port_dest = int(port_dest)
                    except ValueError:
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        resp = add_proxy_header(resp, IP, PORT)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)
                        self.wfile.write(resp)
                        print evento
                        break

                    for linea_pet in lista_cadena:
                        if linea_pet != "":
                            datos = linea_pet.split('=')
                            if len(datos) == 2:
                                dicc_sdp[datos[0]] = datos[1]

                    emisor = dicc_sdp['o'].split()[0]
                    ip_emisor = dicc_sdp['o'].split()[1]
                    if not uaclient.check_ip(ip_emisor):
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        resp = add_proxy_header(resp, IP, PORT)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)
                        self.wfile.write(resp)
                        print evento
                        break

                    if emisor not in dicc_client.keys():
                        descrip = "SIP/2.0 404 User Not Found\r\n\r\n"
                        descrip = add_proxy_header(descrip, IP, PORT)
                        self.wfile.write(descrip)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento,
                        print "Emisor no registrado"
                        self.wfile.write(evento)
                        evento = mi_log.make_event('envio', descrip,
                                                   dir_ip, dir_port_s)
                        print evento
                        break

                    mi_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    mi_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    mi_socket.connect((ip_dest, port_dest))
                    try:
                        print 'Reenviando a ' + dir_dest
                        cadena = add_proxy_header(cadena, IP, PORT)
                        evento = mi_log.make_event('envio', cadena,
                                                   ip_dest, str(port_dest))
                        mi_socket.send(cadena)
                        data = mi_socket.recv(1024)
                        print "Recibido: " + data
                        evento = mi_log.make_event('recepcion', data,
                                                   ip_dest, str(port_dest))

                        emisor_ip = dicc_client[emisor][0]
                        emisor_port = str(dicc_client[emisor][1])
                        print "Reenviando respuesta a " + str(dicc_sdp['o']),
                        print emisor_port
                        data = add_proxy_header(data, IP, PORT)
                        self.wfile.write(data)
                        evento = mi_log.make_event('envio', data,
                                                   dir_ip, dir_port_s)
                        print evento
                    except socket.error:
                        descrip = "No server listening at " + ip_dest
                        descrip = descrip + " port " + str(port_dest)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        self.wfile.write(evento)
                        break

                elif list_words[0] == 'ACK':
                    lista_cadena = cadena.split('\r\n')
                    peticion = lista_cadena[0].split()
                    dir_dest = peticion[1].split(":")[1]
                    ip_dest = dicc_client[dir_dest][0]
                    port_dest = dicc_client[dir_dest][1]

                    if not uaclient.check_ip(ip_dest):
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        resp = add_proxy_header(resp, IP, PORT)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)
                        self.wfile.write(resp)
                        print evento
                        break

                    try:
                        port_dest = int(port_dest)
                    except ValueError:
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        resp = add_proxy_header(resp, IP, PORT)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)
                        self.wfile.write(resp)
                        print evento
                        break

                    mi_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    mi_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    mi_socket.connect((ip_dest, port_dest))
                    try:
                        print 'Reenviando a ' + dir_dest
                        cadena = add_proxy_header(cadena, IP, PORT)
                        evento = mi_log.make_event('envio', cadena,
                                                   ip_dest, str(port_dest))
                        mi_socket.send(cadena)
                    except socket.error:
                        descrip = "No server listening at " + ip_dest
                        descrip = descrip + " port " + str(port_dest)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        self.wfile.write(evento)
                        break

                elif list_words[0] == 'BYE':
                    lista_cadena = cadena.split('\r\n')
                    peticion = lista_cadena[0].split()
                    dir_dest = peticion[1].split(":")[1]
                    ip_dest = dicc_client[dir_dest][0]
                    port_dest = dicc_client[dir_dest][1]

                    if not uaclient.check_ip(ip_dest):
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        resp = add_proxy_header(resp, IP, PORT)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)
                        self.wfile.write(resp)
                        print evento
                        break

                    try:
                        port_dest = int(port_dest)
                    except ValueError:
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        resp = add_proxy_header(resp, IP, PORT)
                        evento = mi_log.make_event('envio', resp,
                                                   dir_ip, dir_port_s)
                        self.wfile.write(resp)
                        print evento
                        break

                    mi_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    mi_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    mi_socket.connect((ip_dest, port_dest))
                    try:
                        print 'Reenviando a ' + dir_dest
                        cadena = add_proxy_header(cadena, IP, PORT)
                        evento = mi_log.make_event('envio', cadena,
                                                   ip_dest, str(port_dest))
                        mi_socket.send(cadena)
                        data = mi_socket.recv(1024)
                        print "Recibido: " + data
                        evento = mi_log.make_event('recepcion', data,
                                                   ip_dest, str(port_dest))
                        print "Reenviando respuesta..."
                        data = add_proxy_header(data, IP, PORT)
                        self.wfile.write(data)
                        evento = mi_log.make_event('envio', data, "", "")
                    except socket.error:
                        descrip = "No server listening at " + ip_dest
                        descrip = descrip + " port " + str(port_dest)
                        evento = mi_log.make_event('error', descrip, '', '')
                        print evento
                        self.wfile.write(evento)
                        break

                elif list_words[0] in meth_not_allowed:
                    descrip = "SIP/2.0 405 Method Not Allowed\r\n\r\n"
                    evento = mi_log.make_event('error', descrip, "", "")
                    descrip = add_proxy_header(descrip, IP, PORT)
                    print evento
                    descrip = add_proxy_header(descrip, IP, PORT)
                    evento = mi_log.make_event('envio', descrip,
                                               dir_ip, dir_port_s)
                    self.wfile.write(descrip)
                    print evento
                else:
                    self.clean_dic()
                    self.register2file()
                    descrip = "SIP/2.0 400 Bad Request\r\n\r\n"

                    evento = mi_log.make_event('error', descrip, "", "")
                    print evento
                    descrip = add_proxy_header(descrip, IP, PORT)
                    evento = mi_log.make_event('envio', descrip,
                                               dir_ip, dir_port_s)
                    self.wfile.write(descrip)
                    print evento

            else:
                break

if __name__ == "__main__":
    # Recopilamos datos de entrada y comprobamos errores
    usage = "Usage: python proxy_registrar.py config"
    server_data = sys.argv
    mi_serv = ""
    meth_not_allowed = ['CANCEL', 'OPTIONS']
    num_rand = random.randint(100000000, 850000000)

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
    dicc_client = {}
    name_database = datos_sesion['database_path']
    user_dir = ""
    user_port = 0
    dir_dest = ""
    datos_dest = []
    dicc_sdp = {}
    rtp_info = {}
    # Creamos servidor SIP y escuchamos
    serv = SocketServer.UDPServer((IP, PORT), SIPRegisterHandler)
    print "Lanzando servidor UDP de SIP...\r\n"
    accion = 'Server ' + server_name + ' listening at port ' + str(PORT)
    evento = mi_log.make_event(accion, '...', '', '')
    print accion + "\r\n"
    serv.serve_forever()
