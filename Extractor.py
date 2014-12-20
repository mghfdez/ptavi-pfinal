#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
# Ignacio Arranz Agueda - ISAM - PTAVI - Practica Final

import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class XMLHandler(ContentHandler):
	def __init__(self):
		# Declaramos la lista
		self.elementos = {}
		self.tags = ["account", "uaserver", "rtpaudio", "regproxy", "log", "audio"]
		self.atributos = {
			"account": ["username", "passwd"],
			"uaserver": ["ip","puerto"],
			"rtpaudio": ["puerto"],
			"regproxy": ["ip", "puerto"],
			"log": ["path"],
			"audio": ["path"]
		}

	def get_tags(self):
	# Devuelve una lista con etiquetas, atributos y contenidos encontrados
		return self.elementos
	
	def startElement(self, name, attrs):
		if name in self.tags:
			for atributo in self.atributos[name]:
				self.elementos[name + '_' + atributo] = attrs.get(atributo, "")         
#============PROGRAMA PRINCIPAL=====================
if __name__ == "__main__":
	try:
		fich = sys.argv[1]
	except IndexError:
		print "Usage: python Extractor.py file.xml"
	parser = make_parser()
	myHandler = XMLHandler()
	parser.setContentHandler(myHandler)
	parser.parse(open(fich))
	print myHandler.get_tags()
