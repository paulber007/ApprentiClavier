# -*- coding: UTF-8 -*-
#Copyright (C) 2013-2016 Noelia Ruiz Mart�nez, other contributors
# Released under GPL2

import addonHandler
addonHandler.initTranslation()

def onInstall():
	for addon in addonHandler.getAvailableAddons():
		if addon.manifest['name'] == "ApprentiClavierAppModule":
			addon.requestRemove()
			break
