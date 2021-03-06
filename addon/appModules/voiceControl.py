#! /usr/bin/env python
# -*- coding: iso-8859-15 -*-
import addonHandler
addonHandler.initTranslation()



from logHandler import log
import speech
import ui
import config
import characterProcessing
from characterProcessing import SYMLVL_SOME,SYMLVL_ALL
import globalVars
import api
import AC_config


# voice options constants
V_RATE = 1

# the voiceControl object
mainVoiceControl = None	
# memorise les options de l'utilisateur
GB_userOptions = {}

		
def getUserOptions():
	global GB_userOptions
	obj = api.getForegroundObject().parent
	try:
		oOptions= obj.children[2].children[1].firstChild
		o = oOptions.children[1]
	except:
		print "Menu options non atteignable"
		return 

	GB_userOptions = {}
	while o :
		try:
			state= False
			if  controlTypes.STATE_CHECKED in  o.states:
				state = True
			
			if o.name != None and len(o.name) >0:
				GB_userOptions[o.name] = state

			o= o.next
		except:
			o = None
			
	#print GB_userOptions	

class SpeedRateVoiceControl(object):
	def __init__(self):
		self.setting = self.getSetting()

		
	def getSetting(self):
		settings = globalVars.settingsRing.settings
		for setting in settings:
			if setting.setting.name == "rate":
				return  setting
		
	def getValue(self):
		return self.setting._get_value()
		
	def setValue(self, value):
		self.setting._set_value(value)
	def getCurrentSetting(self):
		min = self.setting.min
		max = self.setting.max			
		speedRate = self.getValue()
		return (speedRate, min, max)
	
	
class VoiceControl:
	def __init__(self):

		self.speedRateVoiceControl = SpeedRateVoiceControl()
		self.currentSetting ={}
		self.initialize()

	def initialize(self):
		self.saveCurrentSettings()
		# debit moyen  de base r�gl�e au debit  utilisateur en cours
		self.userSpeed=self.setting["speedRate"]
		if AC_config.getDebitGeneralMoyen() != 0:
			# la configuration prevoit un debit moyen  par defaut
			self.userSpeed=AC_config.getDebitGeneralMoyen()
			

		self.OffGenCourant = 0
		self.OffExpliCourant = 0

		(minSpeed, maxSpeed) = AC_config.getMinAndMaxSpeed()

				# OffExpli-OffsetGen sont utilis�s par les options "D�bit Explications" et "D�bit G�n�ral".
		# il sont definis dans le fichier de configuration en pourcentage
		delta = maxSpeed - self.userSpeed
		self.OffGen=(delta*AC_config.getDebitGeneralOffset())/100
		self.OffExpli=(delta*AC_config.getDebitExplicationOffset())/100
		#print"userSpeed: %s, offgen: %s, offExpli: %s" %(self.userSpeed,self.OffGen, self.OffExpli)
		self.offDictee14= (delta*  AC_config.getDebitDictee14Offset())/100

		self.offDictee15= (delta*AC_config.getDebitDictee15Offset())/100
		self.offDictee18 = (delta*AC_config.getDebitDictee18Offset())/100
		#print "offDictee14: %s, offDictee15: %s" % (self.offDictee14, self.offDictee15)
		(self.offDictee19, self.incDictee19) = AC_config.getDebitDictee19OffsetAndIncrement()
		self.offDictee19= (delta*self.offDictee19)/100
		self.incDictee19 = (delta*self.incDictee19)/100
		#print "offDictee19: %s, incDictee19: %s" % (self.offDictee19, self.incDictee19)
		# echo caractere et Peu de ponctuations en entrant dans ApprentiClavier
		self.setTypingEcho(1)
		self.setPunctuationLevel(1)
		# vitesse de la voix  moyenne
		self.ValueVoiceSetting(V_RATE, self.userSpeed + self.OffGenCourant)

		
	def terminate(self):
		self.restoreCurrentSettings()


	def saveCurrentSettings(self):
		self.setting= {}
		self.setting["speakTypedCharacters"] =  config.conf["keyboard"]["speakTypedCharacters"]
		self.setting["speakTypedWords"] =config.conf["keyboard"]["speakTypedWords"]
		self.setting ["symbolLevel"]= config.conf["speech"]["symbolLevel"]
		self.setting["speedRate"] = self.speedRateVoiceControl.getValue()
		



	def restoreCurrentSettings(self):
		config.conf["keyboard"]["speakTypedCharacters"] = self.setting["speakTypedCharacters"]
		config.conf["keyboard"]["speakTypedWords"] =self.setting["speakTypedWords"] 
		config.conf["speech"]["symbolLevel"] = level = self.setting ["symbolLevel"]
		self.speedRateVoiceControl.setValue(self.setting["speedRate"])


	def setOffsetGenEtExpliCourants(self, windowName):
		# on retrouve les options debit general et debit explication avec le titre des fenetres menu principal et sous menu menu lecon
		# comme suit:
		# si titre = "Normal." ou titre commence psans blanc: debit explication normal
		# si titre  = "Rapide." ou il commence par 3 blanc: debit explication rapide
		# si titre == "Lent." ou 1 blanc apres menu: debit general lent
		# si titre == "Moyen." ou deux blancs: debit general moyen
		# si titre == "Vite." ou 3 blancs apres menu : debit general vite


		#pour  debit explication
		if "Rapide." in windowName[:7]:
			# explication rapide
			self.OffExpliCourant = self.OffExpli
			return
		if "Normal." in windowName[:7]:
			# explication normal
			self.OffExpliCourant = 0
			return
			
		# pour debit general
		if "Vite." in windowName[:5]:
			# debit general vite
			self.OffGenCourant = self.OffGen
			return
			if "Moyen." in windowName[:6]:
				# debit  general moyen
				self.OffGenCourant = 0
				return
		
		# en tenant compte de la forme du titre de l'arboressence des menus
		temp = windowName.lstrip()
		if "Menu " in temp[:5]:
			self.OffExpliCourant = 0
			if "   " in windowName[:3]:
				# debit explication rapide
				self.OffExpliCourant = self.OffExpli			
				
			if "Menu   " in temp[:7]:
				# debit general rapide
				self.OffGenCourant = self.OffGen
				
			elif "Menu  " in temp[:7]:
				# debit general moyen
				self.OffGenCourant = 0
			else:
				# debit general lent
				self.OffGenCourant = 0 - self.OffGen
				
		#print"OffGen courant:%s, OffExpli courant: %s" %(self.OffGenCourant, self.OffExpliCourant)

	def updateVoiceSettings(self, windowName, windowText):
		#print "updateVoiceSetting: name= \"%s\"" %(windowName)
		
		self.setOffsetGenEtExpliCourants(windowName)
		# Vitesse vocalisation, et ponctuation, selon la mise en forme du titre de la fen�tre 
		# par defaut, vitesse, ponctuation STANDARD (
		self.MemoSpeed = self.userSpeed + self.OffGenCourant
		punctuation = 1
		typingEcho = 0
		# pour fen�tre "bienvenue"
		if "Bienvenue" in windowName:
			typingEcho = 1
	
	# pour page explicative sans nom
		elif (windowName == "") and (u"pressez espace pour r�p�ter" in windowText.lower()):
						self.MemoSpeed = self.userSpeed + self.OffGenCourant + self.OffExpliCourant

		# Pour page explicatives identifiee
		elif ("Page" in windowName.lstrip()[:4]) :
			self.MemoSpeed = self.userSpeed + self.OffGenCourant + self.OffExpliCourant

		# Pour les  "dict�es 14 
		# on baisse le debit
		elif u"Dict�e 14" in  windowName[:9]:
			self.MemoSpeed = self.userSpeed + self.OffGenCourant - self.offDictee14

		elif u"Le�on 14" in windowName[:8]:
			self.MemoSpeed=  self.userSpeed + self.OffGenCourant - self.offDictee14 
			punctuation = 4
		# Pour les  "dict�es 15 
		elif u"Dict�e 15 A" in windowName[:11]:
			self.MemoSpeed = self.userSpeed + self.OffGenCourant - self.offDictee15 
			
		elif u"Le�on 15 A" in windowName:
			self.MemoSpeed = self.userSpeed + self.OffGenCourant - self.offDictee15 
			punctuation = 4
			
		elif u"Dict�e 15 B" in windowName:
			pass
			
		elif u"Le�on 15 B" in windowName:
			punctuation = 4
			
		elif u"Dict�e 15 C" in windowName:
			self.MemoSpeed = self.userSpeed + self.OffGenCourant + self.offDictee15 

		elif u"Le�on 15 C" in windowName:
			self.MemoSpeed=self.userSpeed + self.OffGenCourantt + self.offDictee15 
			punctuation = 4
		
		# Pour la le�on 18D
		elif u"Le�on 18 D" in windowName:
			self.MemoSpeed=self.userSpeed + self.OffGenCourant +  self.offDictee18  
		
		# Pour les  dict�es 19
		elif u"Dict�e 19 A" in windowName:
			self.MemoSpeed = self.userSpeed + self.OffGenCourant + self.offDictee19 

		elif u"Le�on 19 A" in windowName:
			self.MemoSpeed = self.userSpeed + self.OffGenCourant + self.offDictee19 
			punctuation = 4
			
		elif u"Dict�e 19 B" in windowName:
			self.MemoSpeed =self.userSpeed +  self.OffGenCourant + self.offDictee19 + self.incDictee19 

		elif u"Le�on 19 B" in windowName:
			self.MemoSpeed =self.userSpeed +  self.OffGenCourant + self.offDictee19 + self.incDictee19 
			punctuation = 4
		elif u"Dict�e 19 C" in windowName:
			self.MemoSpeed =self.userSpeed +  self.OffGenCourant + self.offDictee19 + 2 * self.incDictee19 

		elif u"Le�on 19 C" in windowName:
			self.MemoSpeed =self.userSpeed +  self.OffGenCourant + self.offDictee19 + 2 * self.incDictee19 
			punctuation = 4 
		elif u"Dict�e 19 D" in windowName:
			self.MemoSpeed =self.userSpeed +  self.OffGenCourant + self.offDictee19 + 3 * self.incDictee19 

		elif u"Le�on 19 D" in windowName:
			self.MemoSpeed =self.userSpeed +  self.OffGenCourant + self.offDictee19 + 3 * self.incDictee19 
			punctuation = 4
		
		# on positionne le debit, la ponctuation et l'echo caractere
		self.ValueVoiceSetting(V_RATE,self.MemoSpeed)
		self.setPunctuationLevel(punctuation)
		self.setTypingEcho(typingEcho)
		#print "debit: %s, punctuation: %s, echo: %s" %(self.MemoSpeed, punctuation, typingEcho)
		#speech.speakMessage(str(self.MemoSpeed))
		#print "updateVoiceSetting: fin"

			
	def ValueVoiceSetting (self,iSetting , ValidValue):

		(speedRate, minRate, maxRate) = self.getSettingInformation (iSetting)
		speedRate= ValidValue * (maxRate - minRate) / 100
		if (speedRate < minRate):
			speedRate = minRate
			
		elif (speedRate > maxRate):
			speedRate = maxRate

		self.setVoiceSetting (iSetting,speedRate )


	def getSettingInformation (self, iSetting):
		if iSetting == V_RATE:
			return self.speedRateVoiceControl.getCurrentSetting()

	
	
	def setVoiceSetting (self,iSetting, value):
		if iSetting == V_RATE:
			self.speedRateVoiceControl.setValue(value)

	def setPunctuationLevel(self, levelValue):
		if levelValue == 1:
			level = SYMLVL_SOME
		elif levelValue == 4:
			level =SYMLVL_ALL
		else:
			return
		
		config.conf["speech"]["symbolLevel"] = level
	
	def setTypingEcho(self, echo):
		# word echo off 
		config.conf["keyboard"]["speakTypedWords"]=False
		if echo == 0:
			# char echo off
			config.conf["keyboard"]["speakTypedCharacters"]=False

		elif echo == 1:
			# characterecho on
			config.conf["keyboard"]["speakTypedCharacters"]=False
		
		
def initialize():
	global mainVoiceControl
	#print("voiceControl initialize")
	AC_config.Load()
	mainVoiceControl = VoiceControl()



def terminate():
	global mainVoiceControl
#	print ("voiceControl terminate")
	if mainVoiceControl != None:
		mainVoiceControl.terminate()
		mainVoiceControl = None
		
def updateSettings(obj,windowText = ""):
	if mainVoiceControl == None:
		return

	windowName = obj.name
	if windowName == None:
		windowName = ""


	mainVoiceControl.updateVoiceSettings(windowName, windowText)
	