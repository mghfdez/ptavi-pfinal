#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - Miguel Angel Fernandez Sanchez
"""
Programa cliente que abre un socket a un servidor
"""

#Pregunta: Cuando abrimos el fichero de log, ¿machacamos contenido anterior?

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
    datime = time.strftime("%Y%m%d%Y%H%M%S", time.gmtime())
    linea = str(datime) + ' ' + evento + '\r\n'
    fichero.write(linea)

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
    lista_ack = ['SIP/2.0', '100', 'Trying', 'SIP/2.0', '180',
             'Ringing', 'SIP/2.0', '200', 'OK']
    VER = "SIP/2.0"
    datos_sesion = mi_user.get_tags()
    log_path = str(datos_sesion['log_path'])
    log_fich = open(log_path, 'w')
    log_fich.close()
    log_fich = open(log_path, 'a')
    evento = formar_evento('Starting','...','','')
    write_log(log_fich, evento)

    METODO = arg_term[2]
    OPCION = arg_term[3]
    USER_NAME = datos_sesion['account_username']
    RECEPTOR = ""
    EXPIRES = ""
    DIR_SIP = ""
    if METODO == 'REGISTER':
        try:
            EXPIRES = int(OPCION)
            DIR_SIP = USER_NAME
        except ValueError:
            print usage
            # Imprimir en fichero de log todos los errores??
            raise SytemExit
    else:
        RECEPTOR = OPCION
        DIR_SIP = RECEPTOR
    
    # Comprobamos si el método es conocido
    if METODO not in method_list:
        print usage
        raise SystemExit

    # Dirección IP del servidor.
    IP_SERVER = datos_sesion['uaserver_ip']
    # Comprobamos si el puerto introducido es correcto

    try:
        PORT_SERVER = int(datos_sesion['uaserver_puerto'])
        
    except ValueError:
        print usage
        raise SystemExit

    # Contenido que vamos a enviar
    LINE = METODO + " sip:" + DIR_SIP
    if METODO == 'REGISTER':
        LINE = LINE + ":" + "MY_PORT" + " " + VER + '\r\n'
        LINE = LINE + "Expires: " + str(EXPIRES) + '\r\n\r\n'
        # ¿como puedo saber en que puerto estoy escuchando?
    elif METODO == 'INVITE':
        LINE = LINE + " " + VER + "\r\n" + "Content-Type: application/sdp"
        LINE = LINE + "\r\n\r\n" + "v=0" + "\r\n" + "o=" + USER_NAME + " MY_IP"
        LINE = LINE + "\r\n" + "s=KnockKnockKnockPenny" + "\r\n" + "t=0"
        LINE = LINE + "\r\n" + "m=audio " + "RTP_PORT" + " RTP" + "\r\n\r\n"
    elif METODO == 'BYE':
        LINE = LINE + " " + VER + "\r\n\r\n"

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto

    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((IP_SERVER, PORT_SERVER))

    # Comprobamos si hay un servidor escuchando
    #Imprimimos trazas por el terminal y en el fichero de log
    try:
        print "Enviando: " + LINE
        evento = formar_evento('envio', LINE, IP_SERVER, str(PORT_SERVER))
        write_log(log_fich, evento)
        my_socket.send(LINE + '\r\n')
        data = my_socket.recv(1024)
        evento = formar_evento('recepcion', data, '', '')
        write_log(log_fich, evento)
        print "Recibido: " + data
    except socket.error:
        descrip = "No server listening at " + IP_SERVER
        descrip = descrip + " port " + str(PORT_SERVER)
        evento = formar_evento('error', descrip,'','')
        write_log(log_fich, evento)
        print "Error: " + descrip
        evento = formar_evento('Finishing', '...','','')
        write_log(log_fich, evento)
        raise SystemExit

    if data.split() == lista_ack:
        LINE2 = 'ACK sip:' + USER_NAME + " " + VER
        print "Enviando: " + LINE2
        my_socket.send(LINE2 + '\r\n\r\n')
        data2 = my_socket.recv(1024)
        print "Recibido: " + data2
    print "Terminando socket..."

    # Cerramos todo
    my_socket.close()
    print "Fin."
