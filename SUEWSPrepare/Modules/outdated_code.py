    #OLD IMPORTS
        from tabs.cond_tab import CondTab
        from tabs.heat_tab import HeatTab
        from tabs.imp_tab import ImpTab
        from tabs.irr_tab import IrrTab
        from tabs.OHMcoef_tab import OHMCoefTab
        from tabs.prof_tab import ProfTab
        from tabs.snow_tab import Snow
        from tabs.soil_tab import SoilTab
        from tabs.veg_tab import VegTab
        from tabs.water_tab import Water
        from tabs.waterdist_tab import WaterDistTab

        # self.conductance = CondTab()
        # self.widgetlist.append(self.conductance)
        # self.sheetlist.append(self.condsheet)
        # self.titlelist.append("Surface conductance parameters")
        # self.heat_tab = HeatTab()
        # self.widgetlist.append(self.heat_tab)
        # self.sheetlist.append(self.heatsheet)
        # self.titlelist.append("Modelling anthropogenic heat flux ")
        # self.imp_paved = ImpTab()
        # self.widgetlist.append(self.imp_paved)
        # self.sheetlist.append(self.impsheet)
        # self.titlelist.append("Paved surface characteristics")
        # self.imp_buildings = ImpTab()
        # self.widgetlist.append(self.imp_buildings)
        # self.sheetlist.append(self.impsheet)
        # self.titlelist.append("Building surface characteristics")
        # self.irr_tab = IrrTab()
        # self.widgetlist.append(self.irr_tab)
        # self.sheetlist.append(self.irrsheet)
        # self.titlelist.append("Modelling irrigation")
        # self.imp_baresoil = ImpTab()
        # self.widgetlist.append(self.imp_baresoil)
        # self.sheetlist.append(self.impsheet)
        # self.titlelist.append("Bare soil surface characteristics")
        # #self.OHM_tab = OHMCoefTab()
        # self.prof_snow1 = ProfTab()
        # self.widgetlist.append(self.prof_snow1)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Snow clearing profile (Weekdays)")
        # self.prof_snow2 = ProfTab()
        # self.widgetlist.append(self.prof_snow2)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Snow clearing profile (Weekends)")
        # self.prof_energy1 = ProfTab()
        # self.widgetlist.append(self.prof_energy1)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Energy use profile (Weekdays)")
        # self.prof_energy2 = ProfTab()
        # self.widgetlist.append(self.prof_energy2)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Energy use profile (Weekends)")
        # self.prof_wateruse1 = ProfTab()
        # self.widgetlist.append(self.prof_wateruse1)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Water use profile (Manual irrigation, Weekdays)")
        # self.prof_wateruse2 = ProfTab()
        # self.widgetlist.append(self.prof_wateruse2)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Water use profile (Manual irrigation, Weekends)")
        # self.prof_wateruse3 = ProfTab()
        # self.widgetlist.append(self.prof_wateruse3)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Water use profile (Automatic irrigation, Weekdays)")
        # self.prof_wateruse4 = ProfTab()
        # self.widgetlist.append(self.prof_wateruse4)
        # self.sheetlist.append(self.profsheet)
        # self.titlelist.append("Water use profile (Automatic irrigation, Weekends)")
        # self.snow = Snow()
        # self.widgetlist.append(self.snow)
        # self.sheetlist.append(self.snowsheet)
        # self.titlelist.append("Snow surface characteristics")
        # #self.soil_tab = SoilTab()
        # self.water = Water()
        # self.widgetlist.append(self.water)
        # self.sheetlist.append(self.watersheet)
        # self.titlelist.append("Water surface characteristics")
        # #self.waterdist_tab = WaterDistTab()
        # self.veg_evergreen = VegTab()
        # self.widgetlist.append(self.veg_evergreen)
        # self.sheetlist.append(self.vegsheet)
        # self.titlelist.append("Evergreen surface characteristics")
        # self.veg_decidious = VegTab()
        # self.widgetlist.append(self.veg_decidious)
        # self.sheetlist.append(self.vegsheet)
        # self.titlelist.append("Decidious surface characteristics")
        # self.veg_grass = VegTab()
        # self.widgetlist.append(self.veg_grass)
        # self.sheetlist.append(self.vegsheet)
        # self.titlelist.append("Grass surface characteristics")

            self.conductance = TemplateWidget()
        self.widgetlist.append(self.conductance)
        self.sheetlist.append(self.condsheet)
        self.titlelist.append("Surface conductance parameters")
        self.heat_tab = TemplateWidget()
        self.widgetlist.append(self.heat_tab)
        self.sheetlist.append(self.heatsheet)
        self.titlelist.append("Modelling anthropogenic heat flux ")
        self.imp_paved = TemplateWidget()
        self.widgetlist.append(self.imp_paved)
        self.sheetlist.append(self.impsheet)
        self.titlelist.append("Paved surface characteristics")
        self.imp_buildings = TemplateWidget()
        self.widgetlist.append(self.imp_buildings)
        self.sheetlist.append(self.impsheet)
        self.titlelist.append("Building surface characteristics")
        self.irr_tab = TemplateWidget()
        self.widgetlist.append(self.irr_tab)
        self.sheetlist.append(self.irrsheet)
        self.titlelist.append("Modelling irrigation")
        self.imp_baresoil = TemplateWidget()
        self.widgetlist.append(self.imp_baresoil)
        self.sheetlist.append(self.impsheet)
        self.titlelist.append("Bare soil surface characteristics")
        #self.OHM_tab = OHMCoefTab()
        self.prof_snow1 = TemplateWidget()
        self.widgetlist.append(self.prof_snow1)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Snow clearing profile (Weekdays)")
        self.prof_snow2 = TemplateWidget()
        self.widgetlist.append(self.prof_snow2)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Snow clearing profile (Weekends)")
        self.prof_energy1 = TemplateWidget()
        self.widgetlist.append(self.prof_energy1)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Energy use profile (Weekdays)")
        self.prof_energy2 = TemplateWidget()
        self.widgetlist.append(self.prof_energy2)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Energy use profile (Weekends)")
        self.prof_wateruse1 = TemplateWidget()
        self.widgetlist.append(self.prof_wateruse1)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Water use profile (Manual irrigation, Weekdays)")
        self.prof_wateruse2 = TemplateWidget()
        self.widgetlist.append(self.prof_wateruse2)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Water use profile (Manual irrigation, Weekends)")
        self.prof_wateruse3 = TemplateWidget()
        self.widgetlist.append(self.prof_wateruse3)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Water use profile (Automatic irrigation, Weekdays)")
        self.prof_wateruse4 = TemplateWidget()
        self.widgetlist.append(self.prof_wateruse4)
        self.sheetlist.append(self.profsheet)
        self.titlelist.append("Water use profile (Automatic irrigation, Weekends)")
        self.snow = TemplateWidget()
        self.widgetlist.append(self.snow)
        self.sheetlist.append(self.snowsheet)
        self.titlelist.append("Snow surface characteristics")
        #self.soil_tab = SoilTab()
        self.water = TemplateWidget()
        self.widgetlist.append(self.water)
        self.sheetlist.append(self.watersheet)
        self.titlelist.append("Water surface characteristics")
        #self.waterdist_tab = WaterDistTab()
        self.veg_evergreen = TemplateWidget()
        self.widgetlist.append(self.veg_evergreen)
        self.sheetlist.append(self.vegsheet)
        self.titlelist.append("Evergreen surface characteristics")
        self.veg_decidious = TemplateWidget()
        self.widgetlist.append(self.veg_decidious)
        self.sheetlist.append(self.vegsheet)
        self.titlelist.append("Decidious surface characteristics")
        self.veg_grass = TemplateWidget()
        self.widgetlist.append(self.veg_grass)
        self.sheetlist.append(self.vegsheet)
        self.titlelist.append("Grass surface characteristics")

        self.paved_tab = PavedTab()
        self.tablist.append(self.paved_tab)
        self.buildings_tab = BuildingsTab()
        self.tablist.append(self.buildings_tab)
        self.baresoil_tab = BareSoilTab()
        self.tablist.append(self.baresoil_tab)
        self.evergreen_tab = EvergreenTab()
        self.tablist.append(self.evergreen_tab)
        self.decidious_tab = DecidiousTab()
        self.tablist.append(self.decidious_tab)
        self.grass_tab = GrassTab()
        self.tablist.append(self.grass_tab)
        self.water_tab = WaterTab()
        self.tablist.append(self.water_tab)
        self.conductance_tab = ConductanceTab()
        self.tablist.append(self.conductance_tab)
        self.snow_tab = SnowTab()
        self.tablist.append(self.snow_tab)
        self.anthro_tab = AnthroTab()
        self.tablist.append(self.anthro_tab)
        self.energy_tab = EnergyTab()
        self.tablist.append(self.energy_tab)
        self.irrigation_tab = IrrigationTab()
        self.tablist.append(self.irrigation_tab)
        self.wateruse_tab = WaterUseTab()
        self.tablist.append(self.wateruse_tab)

        self.main_tab = MainTab()
        sm.setup_maintab(self.main_tab, self.iface)

         self.paved_tab.Layout.addWidget(self.imp_paved)

        self.buildings_tab.Layout.addWidget(self.imp_buildings)

        self.baresoil_tab.Layout.addWidget(self.imp_baresoil)

        self.evergreen_tab.Layout.addWidget(self.veg_evergreen)

        self.decidious_tab.Layout.addWidget(self.veg_decidious)

        self.grass_tab.Layout.addWidget(self.veg_grass)

        self.water_tab.Layout.addWidget(self.water)

        self.conductance_tab.Layout.addWidget(self.conductance)

        self.snow_tab.Layout.addWidget(self.snow)
        self.snow_tab.Layout2.addWidget(self.prof_snow1)
        self.snow_tab.Layout2.addWidget(self.prof_snow2)

        self.anthro_tab.Layout.addWidget(self.heat_tab)

        self.energy_tab.Layout.addWidget(self.prof_energy1)
        self.energy_tab.Layout.addWidget(self.prof_energy2)

        self.irrigation_tab.Layout.addWidget(self.irr_tab)

        self.wateruse_tab.Layout.addWidget(self.prof_wateruse1)
        self.wateruse_tab.Layout.addWidget(self.prof_wateruse2)
        self.wateruse_tab.Layout2.addWidget(self.prof_wateruse3)
        self.wateruse_tab.Layout2.addWidget(self.prof_wateruse4)

        self.dlg.tabWidget.addTab(self.main_tab, "Main settings")
        self.dlg.tabWidget.addTab(self.paved_tab, "Paved")
        self.dlg.tabWidget.addTab(self.buildings_tab, "Building")
        self.dlg.tabWidget.addTab(self.baresoil_tab, "Bare Soil")
        self.dlg.tabWidget.addTab(self.evergreen_tab, "Evergreen")
        self.dlg.tabWidget.addTab(self.decidious_tab, "Decidious")
        self.dlg.tabWidget.addTab(self.grass_tab, "Grass")
        self.dlg.tabWidget.addTab(self.water_tab, "Water")
        self.dlg.tabWidget.addTab(self.conductance_tab, "Conductance")
        self.dlg.tabWidget.addTab(self.snow_tab, "Snow")
        self.dlg.tabWidget.addTab(self.anthro_tab, "Anthropogenic")
        self.dlg.tabWidget.addTab(self.energy_tab, "Energy")
        self.dlg.tabWidget.addTab(self.irrigation_tab, "Irrigation")
        self.dlg.tabWidget.addTab(self.wateruse_tab, "Water Use")




    #OLD METHODS
    def make_editable(self, widget, sheet):
        code = widget.comboBox.currentText()
        #QgsMessageLog.logMessage("code:" + str(code) + " " + str(type(code)), level=QgsMessageLog.CRITICAL)
        code = int(code)
        for row in range(3, sheet.nrows):
            val = sheet.cell_value(row, 0)
            #QgsMessageLog.logMessage("val:" + str(val) + " " + str(type(val)), level=QgsMessageLog.CRITICAL)
            if val == code:
                values = sheet.row_values(row, 1)
                #QgsMessageLog.logMessage(str(values), level=QgsMessageLog.CRITICAL)
                for x in range(0,len(values)):
                    if values[x] == "!":
                        break
                    exec "widget.lineEdit_" + str(x+1) + ".setEnabled(1)"
                break

    def make_non_editable(self, widget, sheet):
        code = widget.comboBox.currentText()
        #QgsMessageLog.logMessage("code:" + str(code) + " " + str(type(code)), level=QgsMessageLog.CRITICAL)
        code = int(code)
        for row in range(3, sheet.nrows):
            val = sheet.cell_value(row, 0)
            #QgsMessageLog.logMessage("val:" + str(val) + " " + str(type(val)), level=QgsMessageLog.CRITICAL)
            if val == code:
                values = sheet.row_values(row, 1)
                #QgsMessageLog.logMessage(str(values), level=QgsMessageLog.CRITICAL)
                for x in range(0,len(values)):
                    if values[x] == "!":
                        break
                    exec "widget.lineEdit_" + str(x+1) + ".setEnabled(0)"
                break


    def setup_values_outdated(self, widget, filename):
        file_path = self.plugin_dir + '/Input/' + filename
        code = int(widget.comboBox.currentText())
        if os.path.isfile(file_path):
            with open(file_path) as file:
                next(file)
                next(file)
                for line in file:
                    split = line.split()
                    code_file = split[0]
                    if int(code_file) == code:
                        for x in range(1, len(split)):
                            if split[x] == "!":
                                explanation = ""
                                for y in range(x+1, len(split)):
                                    explanation += str(split[y])
                                    explanation += " "
                                widget.exp_label.setText(explanation)
                                break
                            exec "widget.lineEdit_" + str(x) + ".setText(str(" + split[x] + "))"
                        break
        else:
            QMessageBox.critical(None, "Error", "Could not find the file:" + filename)


    def setup_combo_outdated(self, widget, filename):
        file_path = self.plugin_dir + '/Input/' + filename
        if os.path.isfile(file_path):
            with open(file_path) as file:
                #QgsMessageLog.logMessage(file_path, level=QgsMessageLog.CRITICAL)
                next(file)
                next(file)
                for line in file:
                    #QgsMessageLog.logMessage(line, level=QgsMessageLog.CRITICAL)
                    split = line.split()
                    code = split[0]
                    if int(code) == -9:
                        break
                    #elif isinstance(code, int):
                    else:
                        widget.comboBox.addItem(code)
        else:
            QMessageBox.critical(None, "Error", "Could not find the file:" + filename)


      def test_excel(self):
        #wb = openpyxl.load_workbook(self.file_path)
        wb = copy(self.data)
        sheet = self.get_sheet_by_name(wb, self.impsheet.name)
        sheet.write(35, 0, "test")
        wb.save(self.output_path + '/test.xls')

    def test_shapefile(self):
        #skapar referens till vektorlagret, jag gör det genom sökvägen för filen men du kommer antagligen göra det genom combomanager eller liknande
        vlayer = QgsVectorLayer(self.input_path + "grid_barb.shp", "vector layer", "ogr")
        #Tar reda på antalet kollumner i attributformuläret innan några läggs till
        current_index_length = len(vlayer.dataProvider().attributeIndexes())
        #sökväg till textfilen med inputs
        file_path = self.input_path + self.test_file
        #kollar om textfilen finns i sökvägen
        if os.path.isfile(file_path):
            with open(file_path) as file:
                #läser första raden i filen
                line = file.readline()
                #gör raden till en lista med varje "ord" som ett inlägg
                line_split = line.split()
                #hämtar vektorlagrets kapaciteter (Typ ändra attributdata, geometri osv)
                caps = vlayer.dataProvider().capabilities()
                #kollar om vektorlagret kan antera ändringar av attributdata
                if caps & QgsVectorDataProvider.AddAttributes:
                    #Lägger till nya kollumner utifrån första raden i textfilen. Börjar på 1 och inte 0 eftersom första inlägget är id
                    for x in range(1, len(line_split)):
                        #Lägger till varje fält som följer efter id i första raden (Typ pai).
                        #Den första variabeln i QgsField är en string, det andra definierar den data som ska sparas i kollumnen.
                        #Tror att det kanske är här det gått fel för dig tidigare.
                        #Det som för tillfället är acceptabelt är String, Int eller Double och inlägg i kollumnen MÅSTE matcha den valda definitionen.
                        #Om man till exempel skapar en kollumn för integers och sedan försöker lägga in en stringvariabel kommer inget inlägg göras.
                        #Eftersom det mesta i textfilen är decimaltal valde jag Double men String hade också fungerat
                        # å länge som det man väljer att skicka in till kollumnen är variabler i det valda formatet. str(0.5) funkar med andra ord
                        #för en kollumn av formatet String men inte enbart 0.5.
                        vlayer.dataProvider().addAttributes([QgsField(line_split[x], QVariant.Double)])
                    #Skapar en tom python dictionary, det är genom de här som attributdata läggs till i attributformuläret.
                    attr_dict = {}
                    #Läser varje rad som följer efter den första i textfilen.
                    for line in file:
                        #Rensar dict:en.
                        attr_dict.clear()
                        #delar upp den lästa raden
                        split = line.split()
                        #första värdet i raden är id för den "Feature" som radens information ska läggas till i.
                        idx = int(split[0])
                        #Ittererar över varje värde i raden efter id
                        for x in range(1, len(split)):
                            #Lägger till "värdepar" till dict:en, formatet ser ut som {Nyckel: Värde, Nyckel: Värde} kan man säga.
                            #för att Qgis ska lägga till värdena korrekt krävs formatet {Kollumn Index: Värde, Kollumn Index: Värde}
                            #T ex: {1: "detta läggs till i kollumn med index 1 för en senare definerad "Feature", 2: "detta läggs till i kollumn 2 osv"}
                            #Eftersom detta är en lite "klumpig" implementation kommer alltid nya kollumner läggas till när metoden körs. Därför hämtar vi
                            #kollumn index INNAN några kollumner lagts till. Utifrån tidigare index kan vi sedan räkna ut vad index kommer vara
                            # för alla kollumner vi lagt till. Med varje kollumn idex parar vi ihop det värde från raden vi läst.
                            attr_dict[current_index_length + x - 1] = float(split[x])
                        #Lägger till alla kollumnvärden i den skapade dict:en till "Feature" med id: idx
                        vlayer.dataProvider().changeAttributeValues({idx: attr_dict})
                    #uppdaterar fält
                    vlayer.updateFields()
                else:
                    QMessageBox.critical(None, "Error", "Vector Layer does not support adding attributes")
        else:
            QMessageBox.critical(None, "Error", "Could not find the file:" + self.test_file)



