#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
IGNACIO ARRANZ ÁGUEDA - ISAM - PTAVI - PRACTICA FINAL - PROXY_REGISTRAR
"""

import SocketServer
import sys
import time
import socket
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


dic_user = {}
metodos = ("REGISTER", "INVITE", "BYE", "ACK")


def log_status(Estado):
    fich = open("LOG_PROXY.txt", "a")
    fich.write(time.strftime('%Y%m%d%H%M%S '))
    fich.write(Estado+"\r")


def preconf(dic_user, fich_reg):
    fich_reg = open(fich_reg, "r")

    for line in fich_reg:
        line = line.split()
        var_aux = line[0]
        if var_aux != "User":
            dic_user[var_aux] = [line[1], line[2], line[4], line[3]]
    print
    print "Usuarios cargados en el archivo:"
    print "================================"
    print dic_user

    fich_reg.close()

# ================================ OBJETOS =================================


class XMLHandler(ContentHandler):
    """
    Clase que guarda en un fichero los usuarios registrados y comprueba
    si contiene alguno caducado (Expires = 0) y lo saca del registro.
    """
    def __init__(self):
        # Declaramos el diccionario
        self.elementos = {}
        self.tags = ["server", "database", "log"]
        self.atributos = {
            "server": ["name", "ip", "puerto"],
            "database": ["path", "passwpath"],
            "log": ["path"],
        }

    def get_tags(self):
        return self.elementos

    def startElement(self, name, attrs):
        if name in self.tags:
            for atributo in self.atributos[name]:
                self.elementos[name + "_" + atributo] = attrs.get(atributo, "")


# ======================== HANDLE =================================
class SIPRegisterHandler(SocketServer.DatagramRequestHandler):
    def reenvio(self, ip, puerto, mensaje):
        """
        Función que abre un socket directo para esperar
        recibir de el las respuestas
        """
        my_socket_resend = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        my_socket_resend.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        my_socket_resend.connect((ip, puerto))

        my_socket_resend.send(mensaje)

        try:
            data = my_socket_resend.recv(1024)
            print "Recibido mensaje del UAserver:"
            print "------------------------------"
            print data

            self.wfile.write(data)

        except socket.error:
            fecha = time.strftime('%Y%m%d%h%M%S', time.gmtime(time.time()))
            print "Error: No server listening at", ip, \
                "port", puerto
            error = "Error: No server listening at " + str(ip) \
                + " port " + str(puerto)
            # Se le comunica al cliente el error
            self.wfile.write(error)
            # LOG - error ------
            log_status(error)
        my_socket_resend.close()

    def delete_expires(self):
        """
        Borrar busca todos los usuarios con Expires = 0 y los apunta
        en una lista. Despues, se recorre esa lista y los borra a todos.
        """
        lista_borrar = []
        for usuario in dic_user:
            if time.time() >= float(dic_user[usuario][-1]) + \
                    float(dic_user[usuario][-2]):
                lista_borrar.append(usuario)
        # Borra de la lista de "Expirados".
        for a_borrar in lista_borrar:
            del dic_user[a_borrar]
            print "- Borrando a: " + a_borrar

    def register2file(self):
        """
        Los elementos del diccionario son volcados a un fichero que
        contiene: Usuario - IP - Expires.
        """
        fich = open("registered.txt", "w")
        fich.write("User\t\t\tIP\t\t\tPuerto\t\tFecha de Registro\tExpires\n")

        for usuario in dic_user:
            salida = usuario + "\t"
            for elementos in dic_user[usuario]:
                    salida = salida + "\t" + str(elementos) + "\t"
            salida = salida + "\n"
            fich.write(salida)
        fich.close()

    def handle(self):
        """
        Manejador que clasifica los mensajes de entrada en un
        diccionario por: Nombre  - IP - Puerto - Hora de entrada.
        """
        # Comprobamos que no hay usuarios con Expires = 0.
        self.delete_expires()
        # Registramos la entrada en el fichero.
        self.register2file()
        # Recoge el mensaje de entrada la IP y Puerto del cliente.
        address = self.client_address[0]
        port = self.client_address[1]
        while 1:
            line = self.rfile.read()
            if not line:
                break
            else:
                if "\r\n\r\n" in line:
                    print "MENSAJE DE ENTRADA: "
                    print "==================="
                    print line
                    mensaje = line
                    line = line.split()
# ========================= REGISTER ======================================
                    if line[0] == "REGISTER" and line[2] == "SIP/2.0":
                        # LOG -- REGISTER -------
                        Reg_log = "Received " + mensaje.replace("\r\n", " ")
                        log_status(Reg_log)
                        # ------------------
                        line[1] = line[1].split(":")
                        reply = "SIP/2.0 200 OK\r\n\r\n"
                        self.wfile.write(reply)
                        # Si Expires es == 0:
                        if line[-1] == '0':
                            if line[1][1] in dic_user:
                                del dic_user[line[1][1]]
                                print "Eliminando a: " + line[1][1]
                                print "LISTA DE USUARIOS: " + "\n", dic_user
                        else:
                            # Si Expires != 0 construimos el diccionario.
                            key = line[1][1]
                            value = [
                                address, line[1][2],
                                time.time(), line[-1]
                            ]
                            dic_user[key] = value

                            print "LISTA DE USUARIOS:"
                            print "------------------"
                            print dic_user
                            print
# ========================= INVITE ======================================
                    elif line[0] == "INVITE" and line[2] == "SIP/2.0":
                        # LOG --- INVITE -----------
                        Inv_log = "Received " + mensaje.replace("\r\n", " ")
                        log_status(Inv_log)
                        # ----------------------------
                        if ("sip:" in line[1]) and \
                                ("@" in line[1]) and line[2] == 'SIP/2.0':

                            line[1] = line[1].split(":")

                            if dic_user.has_key(line[1][1]):

                                var_aux = dic_user[str(line[1][1])]
                                puerto_destino = var_aux[1]
                                ip_destino = line[1][1].split("@")[1]

                                self.reenvio(
                                    ip_destino,
                                    int(puerto_destino),
                                    mensaje
                                )
                                # LOG -- Resend INVITE ------
                                Inv_log = "Sent to " + str(line[1][1]) \
                                    + ":" + str(puerto_destino)
                                log_status(Inv_log)
                                # --------------------------
                            else:
                                Answer = "SIP/2.0 404 User not found"
                                self.wfile.write(Answer)
                        else:
                            Answer = "SIP/2.0 400 Bad Request"
# ========================= ACK ======================================
                    elif line[0] == "ACK" and line[2] == 'SIP/2.0':
                        # LOG -- ACK ---------------------
                        Ack_log = "Received " + mensaje.replace("\r\n", " ")
                        log_status(Ack_log)
                        # ---------------------------------
                        line[1] = line[1].split(":")
                        try:
                            var_aux = dic_user[str(line[1][1])]
                            puerto_destino = var_aux[1]
                            ip_destino = line[1][1].split("@")[1]
                            self.reenvio(
                                ip_destino,
                                int(puerto_destino),
                                mensaje
                            )
                            # LOG -- ACK -------------
                            Ack_log = "ReSent to " + str(line[1][1]) \
                                + ":" + str(puerto_destino)
                            log_status(Ack_log)
                            # ----------------------------
                        except "SIP/2.0 404 Not user found":
                            # LOG -- Error --------------
                            Error_log = "SIP/2.0 404 Not user found"
                            log_status(Error_log)
                            # -------------------------
# ========================= BYE ======================================
                    elif line[0] == "BYE" and line[2] == 'SIP/2.0':
                        # LOG -- BYE ------------------
                        Bye_log = "Received " + mensaje.replace("\r\n", " ")
                        log_status(Bye_log)
                        # -----------------------------
                        line[1] = line[1].split(":")

                        if dic_user.has_key(line[1][1]):
                            var_aux = dic_user[str(line[1][1])]
                            puerto_destino = var_aux[1]
                            ip_destino = line[1][1].split("@")[1]

                            self.reenvio(
                                ip_destino,
                                int(puerto_destino),
                                mensaje
                            )
                            # LOG -- BYE --------------------
                            Bye_log = "ReSent to " + str(line[1][1]) \
                                + ":" + str(puerto_destino)
                            log_status(Bye_log)
                            # ------------------------------------
                        else:
                            Answer = "SIP/2.0 404 User not found"
                            self.wfile.write(Answer)

                    elif line[0] not in metodos:
                        self.wfile.write(
                            "SIP/2.0 405 Method"
                            " Not Allowed\r\n\r\n"
                        )
                        # LOG -- ERROR -------
                        Error_log = "SIP/2.0 405 Method Not Allowed"
                        log_status(Error_log)
                        # ---------------------
                else:
                    self.wfile.write("SIP/2.0 400 Bad Request\r\n\r\n")
                    # LOG -- Error ----------------
                    Error_log = "SIP/2.0 400 Bad Request"
                    log_status(Error_log)
                    #--------------------------------
#====================== PROGRAMA PRINCIPAL ==============================
if __name__ == "__main__":
    try:
        fich = sys.argv[1]
    except IndexError:
        print "Usage: python file.py file.xml"
    parser = make_parser()
    myProxy_Registrar = XMLHandler()
    parser.setContentHandler(myProxy_Registrar)
    parser.parse(open(fich))

    LOG_PROXY = myProxy_Registrar.elementos["log_path"]
    SERVER_PORT = int(myProxy_Registrar.elementos["server_puerto"])

    serv = SocketServer.UDPServer(("", SERVER_PORT), SIPRegisterHandler)

    # OPCIONAL -- Preconfiguración del archivo ------------
    fich_reg = myProxy_Registrar.elementos["database_path"]
    preconf(dic_user, fich_reg)
    # -----------------------------------------------------
    print ""
    print "========================================================="
    print "========== Servidor Proxy-Registrar conectado ==========="
    print "========================================================="
    # LOG -- Start ---------
    Start_log = "Starting..."
    log_status(Start_log)
    # -----------------------
    serv.serve_forever()
