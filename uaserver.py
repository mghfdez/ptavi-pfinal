#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - Miguel Angel Fernandez Sanchez
"""
Clase (y programa principal) para un servidor SIP
"""
#¿Hay que copiar otra vez todo el parser? (Clase incluido?)

import SocketServer
import socket
import sys
import os
import time
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
log_fich = open(log_path, 'w')
log_fich.close()
evento = formar_evento('Listening','...','','')
write_log(log_path, evento)
IP = datos_sesion['uaserver_ip']
RTP_INFO = {}
try:
    PORT = int(datos_sesion['uaserver_puerto'])
except ValueError:
    print usage
    raise SystemExit

AUDIO_FILE = str(datos_sesion['audio_path'])

if not os.path.exists(AUDIO_FILE):
    print usage
    raise SystemExit


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
                    evento = formar_evento('envio', resp, ip_clnt, str(port_clnt))
                    write_log(log_path, evento) 
                    break
                evento = formar_evento('recepcion', cadena, ip_clnt, str(port_clnt))
                write_log(log_path, evento) 
                print 'Recibida petición: ' + cadena
                # Gestionamos la peticion dependiendo del método
                if list_words[0] == 'INVITE':
                    lista_cadena = cadena.split('\r\n')
                    for dato in lista_cadena:
                        if dato != "":
                            lista_linea = dato.split('=')
                            if lista_linea[0] == 'm':
                                datos_sdp = lista_linea[1].split()
                                if datos_sdp[0] == 'audio':
                                    RTP_INFO['rtp_port'] = int(datos_sdp[1])
                    correo = list_words[1].split(":")[1]
                    resp = "SIP/2.0 100 Trying\r\n\r\n"
                    #Aqui debe ir la descripcion SDP
                    resp = resp + "SIP/2.0 180 Ringing\r\n\r\n"
                    resp = resp + "SIP/2.0 200 OK\r\n\r\n"
                    self.wfile.write(resp)
                    evento = formar_evento('envio', resp, ip_clnt, str(port_clnt))
                    write_log(log_path, evento)
                elif list_words[0] == 'BYE':
                    resp = "SIP/2.0 200 OK\r\n\r\n"
                    self.wfile.write(resp)
                    evento = formar_evento('envio', resp, ip_clnt, str(port_clnt))
                    write_log(log_path, evento)
                elif list_words[0] == "ACK":
                    audio_prt = RTP_INFO['rtp_port']
                    os.system('chmod 755 mp32rtp')
                    to_exe = './mp32rtp -i ' + ip_clnt
                    to_exe = to_exe + ' -p ' + str(audio_prt) + ' < ' + AUDIO_FILE
                    accion = "Enviando audio a " + ip_clnt + ':'
                    accion = accion + str(audio_prt)
                    print accion
                    os.system(to_exe)
                    evento = formar_evento(accion, "", "", "")
                    write_log(log_path, evento) 
                else:
                    resp = "SIP/2.0 405 Method Not Allowed\r\n\r\n"
                    self.wfile.write(resp)
                    evento = formar_evento('envio', resp, ip_clnt, str(port_clnt))
                    write_log(log_path, evento)
                print 'Respuesta enviada.'
            # Si no hay más líneas salimos del bucle infinito
            else:
                break

if __name__ == "__main__":
    # Creamos servidor de eco y escuchamos
    try:
        serv = SocketServer.UDPServer((IP, PORT), SIPHandler)
        print "Listening..."
        serv.serve_forever()
    except socket.gaierror:
        print usage
        raise SystemExit
