#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica 6 - Miguel Angel Fernandez Sanchez
"""
Clase (y programa principal) para un servidor SIP
"""

import SocketServer
import os
import sys
import socket

# Recopilamos datos de entrada y comprobamos errores
usage = "Usage: python server.py IP port audio_file"
server_data = sys.argv

if len(server_data) != 4:
    print usage
    raise SystemExit
IP = server_data[1]
try:
    PORT = int(server_data[2])
except ValueError:
    print usage
    raise SystemExit
AUDIO_FILE = server_data[3]
if not os.path.exists(AUDIO_FILE):
    print usage
    raise SystemExit


def check_request(lista):
    # Comprueba si la petición recibida esta bien formada
    lista_ok = [3, 'SIP/2.0', 'sip', 2]
    lista_check = ['', '', '', '']
    try:
        # Relleno lista y comparo para saber si los datos son los esperados
        lista_check[0] = len(lista)
        lista_check[1] = lista[2]
        user = lista[1].split(":")
        lista_check[2] = user[0]
        user_data = user[1].split('@')
        lista_check[3] = len(user_data)
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
                ip_client = str(self.client_address[0])
                list_words = cadena.split()
                list_ok = check_request(list_words)
                # Si los datos no son correctos, mandamos mensaje de error
                if not list_ok:
                    self.wfile.write("SIP/2.0 400 Bad Request\r\n\r\n")
                    break
                print 'Recibida petición: ' + cadena
                # Gestionamos la peticion dependiendo del método
                if list_words[0] == 'INVITE':
                    correo = list_words[1].split(":")[1]
                    resp = "SIP/2.0 100 Trying\r\n\r\n"
                    resp = resp + "SIP/2.0 180 Ringing\r\n\r\n"
                    resp = resp + "SIP/2.0 200 OK\r\n\r\n"
                    self.wfile.write(resp)
                elif list_words[0] == 'BYE':
                    self.wfile.write("SIP/2.0 200 OK\r\n\r\n")
                elif list_words[0] == "ACK":
                    os.system('chmod 755 mp32rtp')
                    to_exe = './mp32rtp -i ' + ip_client
                    to_exe = to_exe + ' -p 23032 < ' + AUDIO_FILE
                    print "Enviando audio..."
                    os.system(to_exe)
                else:
                    self.wfile.write("SIP/2.0 405 Method Not Allowed\r\n\r\n")
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
