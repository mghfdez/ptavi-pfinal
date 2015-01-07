#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - Miguel Angel Fernandez Sanchez
"""
Programa cliente que abre un socket a un servidor
"""


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

        self.dicc_config = {'account': ['username', 'passwd'],
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
            frase = frase + "\r\n" + atrib + '="'
            frase += self.dicc_datos[atrib] + '"'
        print frase

    def get_tags(self):
        return self.dicc_datos


class LogConfig:

    def __init__(self, log_path):
        self.log_path = log_path

    def borrar_fichero(self):
        fich = open(self.log_path, 'w')
        fich.close()

    def write_log(self, evento):
        datime = time.strftime("%Y%m%d%Y%H%M%S", time.gmtime())
        linea = str(datime) + ' ' + evento + '\r\n'
        fichero = open(self.log_path, 'a')
        fichero.write(linea)
        fichero.close()

    def make_event(self, tipo, datos, ip, puerto):
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
        self.write_log(frase)
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
    lista_ack = ['SIP/2.0 100 Trying', 'SIP/2.0 180 Ringing',
                 'SIP/2.0 200 OK']
    VER = "SIP/2.0"
    datos_sesion = mi_user.get_tags()
    log_path = str(datos_sesion['log_path'])
    mi_log = LogConfig(log_path)
    evento = mi_log.make_event('Starting', '...', '', '')
    AUDIO_FILE = str(datos_sesion['audio_path'])

    if not os.path.exists(AUDIO_FILE):
        print 'No existe el fichero de audio'
        print usage
        raise SystemExit
    #evento = mi_log.make_event('error','...','','')
    METODO = arg_term[2]
    OPCION = arg_term[3]
    USER_NAME = datos_sesion['account_username']
    RECEPTOR = ""
    EXPIRES = ""
    DIR_SIP = ""
    IP_DEST = ""
    PORT_DEST = 0
    RTP_PORT = datos_sesion['rtpaudio_puerto']
    dicc_sdp = {}
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

    IP_DEST = datos_sesion['regproxy_ip']
    PORT_DEST = int(datos_sesion['regproxy_puerto'])

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto

    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((IP_DEST, PORT_DEST))
    who_am_I = my_socket.getsockname()

    # Contenido que vamos a enviar
    LINE = METODO + " sip:" + DIR_SIP
    if METODO == 'REGISTER':
        LINE += ":" + str(PORT_SERVER) + " " + VER + '\r\n'
        LINE += "Expires: " + str(EXPIRES) + '\r\n\r\n'
    elif METODO == 'INVITE':
        LINE += " " + VER + "\r\n" + "Content-Type: application/sdp"
        LINE += "\r\n\r\n" + "v=0" + "\r\n" + "o=" + USER_NAME + " "
        LINE += IP_SERVER + "\r\n" + "s=KnockKnockKnockPenny"
        LINE += "\r\n" + "t=0"
        LINE += "\r\n" + "m=audio " + str(RTP_PORT) + " RTP" + "\r\n\r\n"
    elif METODO == 'BYE':
        LINE = LINE + " " + VER + "\r\n\r\n"

    # Comprobamos si hay un servidor escuchando
    #Imprimimos trazas por el terminal y en el fichero de log
    try:
        print "Enviando: " + LINE
        evento = mi_log.make_event('envio', LINE, IP_DEST, str(PORT_DEST))
        my_socket.send(LINE + '\r\n')
        data = my_socket.recv(1024)
        print "Recibido: " + data
        evento = mi_log.make_event('recepcion', data, '', '')
    except socket.error:
        descrip = "No server listening at " + IP_DEST
        descrip = descrip + " port " + str(PORT_DEST)
        evento = mi_log.make_event('error', descrip, '', '')
        print "Error: " + descrip
        evento = mi_log.make_event('Finishing', '...', '', '')
        raise SystemExit

    resp_data = data.split('\r\n')
    resp_data_clean = []
    for campo in resp_data:
        if campo != "":
            resp_data_clean.append(campo)

    resp_to_check = resp_data_clean[0:3]

    if resp_to_check == lista_ack:
        #Extraemos el puerto RTP al que enviaremos el audio.
        for linea_resp in resp_data_clean:
            datos = linea_resp.split('=')
            if len(datos) == 2:
                dicc_sdp[datos[0]] = datos[1]

        datos_audio = dicc_sdp['m'].split()
        if datos_audio[0] == 'audio':
            audio_prt = int(datos_audio[1])

        #Enviamos ACK
        LINE2 = 'ACK sip:' + DIR_SIP + " " + VER
        print "Enviando: " + LINE2
        my_socket.send(LINE2 + '\r\n\r\n')
        evento = mi_log.make_event('envio', LINE2, IP_SERVER, str(PORT_SERVER))

        #Enviamos audio
        os.system('chmod 755 mp32rtp')
        to_exe = './mp32rtp -i ' + IP_SERVER
        to_exe = to_exe + ' -p ' + str(audio_prt) + ' < ' + AUDIO_FILE
        os.system(to_exe)
        accion = "Enviando audio a " + IP_SERVER + ':'
        accion += str(audio_prt)
        evento = mi_log.make_event(accion, '', '', '')
        print evento
        print "Terminado envío de audio\r\n"
        data2 = my_socket.recv(1024)
        if data2 != "":
            print "Recibido: " + data2
            evento = mi_log.make_event('recepcion', data2, '', '')
            mi_log.write_log(log_fich, evento)
    print "Terminando socket..."

    # Cerramos todo
    evento = mi_log.make_event('Finishing', '...', '', '')
    my_socket.close()
    print "Fin."
