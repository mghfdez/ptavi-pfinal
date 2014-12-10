#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#Practica Final - Miguel Angel Fernandez Sanchez
"""
Programa cliente que abre un socket a un servidor
"""

import socket
import sys
import os

# Cliente UDP simple.
user_data = sys.argv
method_list = ['REGISTER', 'INVITE', 'BYE']

usage = "Usage: python uaclient.py config method option"
if len(user_data) != 4:
    print usage
    raise SystemExit

try:
    fich_conf = user_data[1]
    if not os.path.exists(fich_conf):
        print 'No existe fichero XML'
        print usage
        raise SystemExit
except IndexError:
    print usage
    raise SystemExit

VER = "SIP/2.0"
METODO = user_data[2]

# Comprobamos si el método es conocido
if METODO not in method_list:
    print usage
    raise SystemExit

# Dirección IP del servidor.
# Comprobamos si el puerto introducido es correcto


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
