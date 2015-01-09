#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - Miguel - UAServer Angel Fernandez Sanchez
"""
Clase (y programa principal) para un servidor SIP
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
    Clase para manejar fichero de configuracion para SIP
    """
    def __init__(self):
        """
        Constructor
        """

        self.dicc_config = {'account': ['username', 'passwd'],
                            'uaserver': ['ip', 'puerto'],
                            'rtpaudio': ['puerto'],
                            'regproxy': ['ip', 'puerto'],
                            'log': ['path'],
                            'audio': ['path']}

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


class SIPHandler(SocketServer.DatagramRequestHandler):
    """
    SIP server class
    """

    def handle(self):

        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            cadena = self.rfile.read()
            if cadena != "":
                ip_clnt = str(self.client_address[0])
                port_clnt = self.client_address[1]
                list_words = cadena.split()
                list_ok = check_request(list_words)
                # Si los datos no son correctos, mandamos mensaje de error
                if not list_ok:
                    resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                    self.wfile.write(resp)
                    evento = mi_log.make_event('envio', resp,
                                               ip_clnt, str(port_clnt))
                    print evento
                    evento = mi_log.make_event('error', resp, "", "")
                    print evento
                    break

                evento = mi_log.make_event('recepcion', cadena,
                                           ip_clnt, str(port_clnt))
                print 'Recibido: ' + cadena

                # Gestionamos la peticion dependiendo del método
                if list_words[0] == 'INVITE':
                    lista_cadena = cadena.split('\r\n')
                    for linea_pet in lista_cadena:
                        if linea_pet != "":
                            datos = linea_pet.split('=')
                            if len(datos) == 2:
                                dicc_sdp[datos[0]] = datos[1]

                    datos_audio = dicc_sdp['m'].split()

                    if datos_audio[0] == 'audio':
                        rtp_info['rtp_port'] = int(datos_audio[1])

                    ip_send = dicc_sdp['o'].split()[1]
                    if not uaclient.check_ip(ip_send):
                        resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                        self.wfile.write(resp)
                        evento = mi_log.make_event('envio', resp,
                                                   ip_clnt, str(port_clnt))
                        print evento
                        evento = mi_log.make_event('error', resp, "", "")
                        print evento
                        break

                    correo = list_words[1].split(":")[1]
                    resp = "SIP/2.0 100 Trying\r\n\r\n"
                    resp += "SIP/2.0 180 Ringing\r\n\r\n"
                    resp += "SIP/2.0 200 OK\r\n\r\n"
                    resp += "\r\n" + "Content-Type: application/sdp"
                    resp += "\r\n\r\n" + "v=0" + "\r\n" + "o=" + mi_dir + " "
                    resp += IP + "\r\n" + "s=KnockKnockKnockPenny"
                    resp += "\r\n" + "t=0" + "\r\n" + "m=audio "
                    resp += str(audio_port) + " RTP" + "\r\n\r\n"

                    #Dejamos ejecutando cvlc
                    to_exe1 = "cvlc rtp://"
                    to_exe1 += IP + ':' + str(audio_port) + ' 2> /dev/null &'
                    print "Ejecutando cvlc..."
                    print to_exe1
                    os.system(to_exe1)

                    #Enviamos respuesta
                    print "Enviando respuesta (200 OK + SDP)..."
                    self.wfile.write(resp)
                    evento = mi_log.make_event('envio', resp,
                                               ip_clnt, str(port_clnt))

                elif list_words[0] == 'BYE':
                    resp = "SIP/2.0 200 OK\r\n\r\n"
                    print "Enviando respuesta..."
                    self.wfile.write(resp)
                    evento = mi_log.make_event('envio', resp,
                                               ip_clnt, str(port_clnt))

                elif list_words[0] == "ACK":
                    ip_send = dicc_sdp['o'].split()[1]
                    audio_prt = rtp_info['rtp_port']
                    os.system('chmod 755 mp32rtp')
                    to_exe2 = './mp32rtp -i ' + ip_send
                    to_exe2 += ' -p ' + str(audio_prt) + ' < ' + AUDIO_FILE
                    accion = "Enviando audio a " + ip_send + ':'
                    accion += str(audio_prt)
                    print accion
                    os.system(to_exe2)
                    evento = mi_log.make_event(accion, "", "", "")
                    print "Terminado envío de audio\r\n"

                elif list_words[0] in meth_not_allowed:
                    resp = "SIP/2.0 405 Method Not Allowed\r\n\r\n"
                    self.wfile.write(resp)
                    evento = mi_log.make_event('error', descrip, "", "")
                    print evento
                    evento = mi_log.make_event('envio', resp,
                                               ip_clnt, str(port_clnt))
                    print evento

                else:
                    resp = "SIP/2.0 400 Bad Request\r\n\r\n"
                    self.wfile.write(resp)
                    evento = mi_log.make_event('error', descrip, "", "")
                    print evento
                    evento = mi_log.make_event('envio', resp,
                                               ip_clnt, str(port_clnt))
                    print evento

            # Si no hay más líneas salimos del bucle infinito
            else:
                break

if __name__ == "__main__":
    # Creamos servidor de eco y escuchamos

    # Recopilamos datos de entrada y comprobamos errores
    usage = "Usage: python uaserver.py config"
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
    mi_log = uaclient.LogConfig(log_path)
    evento = mi_log.make_event('Listening', '...', '', '')
    IP = datos_sesion['uaserver_ip']
    rtp_info = {}
    dicc_sdp = {}
    ip_send = ""
    mi_dir = datos_sesion['account_username']
    meth_not_allowed = ['CANCEL', 'OPTIONS']
    try:
        PORT = int(datos_sesion['uaserver_puerto'])
    except ValueError:
        print usage
        raise SystemExit

    AUDIO_FILE = str(datos_sesion['audio_path'])
    audio_port = datos_sesion['rtpaudio_puerto']

    if not os.path.exists(AUDIO_FILE):
        print usage
        raise SystemExit
    try:
        #Dejamos el servidor escuchando
        serv = SocketServer.UDPServer((IP, PORT), SIPHandler)
        print "Listening..."
        serv.serve_forever()
    except socket.gaierror:
        print usage
        raise SystemExit
