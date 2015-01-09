#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - UAClient - Miguel Angel Fernandez Sanchez
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
        metodo que devuelve el diccionario de elementos
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
        datime = time.strftime("%Y%m%d%H%M%S", time.gmtime())
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
    audio_file = str(datos_sesion['audio_path'])

    if not os.path.exists(audio_file):
        print 'No existe el fichero de audio'
        print usage
        raise SystemExit
    #evento = mi_log.make_event('error','...','','')
    metodo = arg_term[2]
    opcion = arg_term[3]
    user_name = datos_sesion['account_username']
    receptor = ""
    expires = ""
    dir_sip = ""
    ip_dest = ""
    port_dest = 0
    rtp_port = datos_sesion['rtpaudio_puerto']
    dicc_sdp = {}
    if metodo == 'REGISTER':
        try:
            expires = int(opcion)
            dir_sip = user_name
        except ValueError:
            print usage
            # Imprimir en fichero de log todos los errores??
            raise SytemExit
    else:
        receptor = opcion
        dir_sip = receptor

    # Comprobamos si el método es conocido
    if metodo not in method_list:
        print usage
        #raise SystemExit

    # Dirección IP del servidor.
    ip_server = datos_sesion['uaserver_ip']
    # Comprobamos si el puerto introducido es correcto
    try:
        port_server = int(datos_sesion['uaserver_puerto'])
    except ValueError:
        print usage
        raise SystemExit

    ip_dest = datos_sesion['regproxy_ip']
    port_dest = int(datos_sesion['regproxy_puerto'])

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto

    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((ip_dest, port_dest))
    who_am_I = my_socket.getsockname()

    # Contenido que vamos a enviar
    line = metodo + " sip:" + dir_sip
    if metodo == 'REGISTER':
        line += ":" + str(port_server) + " " + VER + '\r\n'
        line += "expires: " + str(expires) + '\r\n\r\n'
    elif metodo == 'INVITE':
        line += " " + VER + "\r\n" + "Content-Type: application/sdp"
        line += "\r\n\r\n" + "v=0" + "\r\n" + "o=" + user_name + " "
        line += ip_server + "\r\n" + "s=KnockKnockKnockPenny"
        line += "\r\n" + "t=0"
        line += "\r\n" + "m=audio " + str(rtp_port) + " RTP" + "\r\n\r\n"
    elif metodo == 'BYE':
        line += " " + VER + "\r\n\r\n"
    else:
        line += " " + VER + "\r\n\r\n"

    # Comprobamos si hay un servidor escuchando
    #Imprimimos trazas por el terminal y en el fichero de log
    try:
        print "Enviando: " + line
        evento = mi_log.make_event('envio', line, ip_dest, str(port_dest))
        my_socket.send(line + '\r\n')
        data = my_socket.recv(1024)
        print "Recibido: " + data
        evento = mi_log.make_event('recepcion', data, '', '')
    except socket.error:
        descrip = "No server listening at " + ip_dest
        descrip = descrip + " port " + str(port_dest)
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
        line2 = 'ACK sip:' + dir_sip + " " + VER
        print "Enviando: " + line2
        my_socket.send(line2 + '\r\n\r\n')
        evento = mi_log.make_event('envio', line2, ip_server, str(port_server))

        #Enviamos audio
        os.system('chmod 755 mp32rtp')
        to_exe = './mp32rtp -i ' + ip_server
        to_exe = to_exe + ' -p ' + str(audio_prt) + ' < ' + audio_file
        os.system(to_exe)
        accion = "Enviando audio a " + ip_server + ':'
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
