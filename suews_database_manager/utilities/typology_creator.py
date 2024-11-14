from pandas import DataFrame, concat
from .database_functions import create_code, save_to_db
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtGui import QImage, QPixmap
import urllib.request, urllib.error, urllib.parse
from qgis.core import QgsMessageLog
from numpy import nan

#################################################################################################
#                                                                                               #
#                                     Typology Creator                                          #
#                                                                                               #
#################################################################################################

def setup_typology_creator(self, dlg, db_dict, db_path):

    def fill_cbox():

        dlg.textEditOrig.clear()
        dlg.textEditDesc.clear()
        dlg.textEditName.clear()
        dlg.textEditAuthor.clear()
        dlg.comboBoxTableSelect.clear()
        dlg.comboBoxTableSelect.addItems((db_dict['Types']['nameOrigin'])) 
        dlg.comboBoxTableSelect.setCurrentIndex(-1)
        dlg.comboBoxPavedType.clear()
        dlg.comboBoxPavedType.addItems((db_dict['NonVeg']['nameOrigin'][db_dict['NonVeg']['Surface'] == 'Paved']))
        dlg.comboBoxBuildingType.clear()
        dlg.comboBoxBuildingType.addItems((db_dict['NonVeg']['nameOrigin'][db_dict['NonVeg']['Surface'] == 'Buildings']))
        for i in [dlg.comboBoxPavedType,dlg.comboBoxBuildingType]:
            i.setCurrentIndex(-1)
        dlg.comboBoxProf.setCurrentIndex(0)
        dlg.comboBoxPeriod.setCurrentIndex(0)
        dlg.label_2.clear()
        dlg.textBrowser_source.clear()


    def check_type():
        if dlg.textEditName.isNull():
            QMessageBox.warning(None, 'Error in Name','Enter a name for new type')
        elif dlg.textEditName.value().startswith('test'):
            QMessageBox.warning(None, 'Error in Name','Please, don´t use test as type name..')
        elif dlg.textEditName.value().startswith('Test'):
            QMessageBox.warning(None, 'Error in Name','Please, don´t use test as type name..')
        # elif dlg.textEditName.value() in db_dict['Types']['Type'].tolist():
        #     QMessageBox.warning(None, 'Error in Name','The suggested type name is already taken.')

        # Origin
        elif dlg.textEditOrig.isNull():
            QMessageBox.warning(None, 'Error in Origin','Enter a Origin for new type')
        # Final - When all is Checked 
        else:
            QMessageBox.information(None, 'Check Complete', 'Your type is compatible with the SUEWS-Database!\nPress Generate New Type to add to your local Database')
            dlg.pushButtonGen.setEnabled(True)

    def changed(): 

        def type_changed(cbox, table, surface):
            urb_type = dlg.comboBoxTableSelect.currentText()
            if urb_type != '':
                indexer =db_dict['Types'][db_dict['Types']['nameOrigin'] == urb_type][surface].item()
                table_indexer = table.loc[indexer,'nameOrigin']
                table_index = cbox.findText(table_indexer)
                cbox.setCurrentIndex(table_index)
        
        type_changed(dlg.comboBoxBuildingType, db_dict['NonVeg'],  'Buildings')
        type_changed(dlg.comboBoxPavedType, db_dict['NonVeg'], 'Paved')
        
        urb_type = dlg.comboBoxTableSelect.currentText()
        if urb_type != '':
            indexer =db_dict['Types']['ProfileType'].loc[db_dict['Types']['nameOrigin'] == urb_type].item()
            if indexer == 'Residential':
                dlg.comboBoxProf.setCurrentIndex(1)
            elif indexer == 'Commercial':
                dlg.comboBoxProf.setCurrentIndex(2)
            elif indexer == 'Industrial':
                dlg.comboBoxProf.setCurrentIndex(3)
            
            indexerPeriod =db_dict['Types']['Period'].loc[db_dict['Types']['nameOrigin'] == urb_type].item()
            if indexerPeriod == 'Pre80':
                dlg.comboBoxPeriod.setCurrentIndex(1)
            elif indexerPeriod == 'Pst80':
                dlg.comboBoxPeriod.setCurrentIndex(2)
            elif indexerPeriod == 'New':
                dlg.comboBoxPeriod.setCurrentIndex(3)


    def typology_info():

        # TODO Update with changed paved/buildings Combobox
        typology_str = dlg.comboBoxTableSelect.currentText()
        dlg.textBrowserTypo.clear()

        if dlg.comboBoxTableSelect.currentIndex() != -1:
            #typology_sel = db_dict['NonVeg'].loc[db_dict['NonVeg']['nameOrigin'] == typology_str]
            typology_sel = db_dict['Types'].loc[db_dict['Types']['nameOrigin'] == typology_str]
            buildID = typology_sel['Buildings'].item()
            PavedID  = typology_sel['Paved'].item()
            wall1ID = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['w1Material'].item()
            wall1Type = db_dict['Spartacus Material'].loc[wall1ID]['Name']
            wall1Th = str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['w1Thickness'],2) * 100)
            wall2ID = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['w2Material'].item()
            wall2Type = db_dict['Spartacus Material'].loc[wall2ID]['Name']
            wall2Th = str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['w2Thickness'],2) * 100)
            wall3ID = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['w3Material'].item()
            wall3Type = db_dict['Spartacus Material'].loc[wall3ID]['Name']
            wall3Th = str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['w3Thickness'],2) * 100)
            
            roof1ID = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['r1Material'].item()
            roof1Type = db_dict['Spartacus Material'].loc[roof1ID]['Name']
            roof1Th = str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['r1Thickness'],2) * 100)
            roof2ID = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['r2Material'].item()
            roof2Type = db_dict['Spartacus Material'].loc[roof2ID]['Name']
            roof2Th = str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['r2Thickness'],2) * 100)
            roof3ID = db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['r3Material'].item()
            roof3Type = db_dict['Spartacus Material'].loc[roof3ID]['Name']
            roof3Th = str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID].loc['Spartacus Surface']]['r3Thickness'],2) * 100)

            dlg.textBrowserTypo.setText(
                'URBAN TYPOLOGY:' + '\n' +
                'Name: ' + typology_sel['Name'].item() + '\n' +
                'Origin: ' + typology_sel['Origin'].item() + '\n' +
                'Description: ' + typology_sel['Description'].item() + '\n' +
                'Construction perion: ' +  typology_sel['Period'].item() + '\n' +
                'Type of land use: ' + typology_sel['ProfileType'].item() + '\n' +
                ' '  + '\n' +
                'ASSOCIATED BUILDING TYPE:' + '\n' +
                'Name: ' + db_dict['NonVeg'].loc[buildID]['Name'] + '\n' +
                'Origin: ' + db_dict['NonVeg'].loc[buildID]['Origin'] + '\n' +
                'Mean albedo (min): ' + str(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[buildID]['Albedo']]['Alb_min'].item()) + '\n' +
                'Mean albedo (max): ' + str(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[buildID]['Albedo']]['Alb_min'].item()) + '\n' +
                'Effective Surface Emissivity: ' + str(db_dict['Emissivity'].loc[db_dict['NonVeg'].loc[buildID]['Emissivity']]['Emissivity'].item()) + '\n' +
                'U-value (roof): ' + str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID]['Spartacus Surface']]['u_value_roof'].item(), 2)) + '\n' +
                'U-value (walls): ' + str(round(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID]['Spartacus Surface']]['u_value_wall'].item(), 2)) + '\n' +
                'Outer wall material: ' + wall1Type + ', thickness = ' + wall1Th + ' cm' + '\n' +
                'Middle wall material: ' + wall2Type + ', thickness = ' + wall2Th + ' cm' + '\n' +
                'Inner wall material: ' + wall3Type + ', thickness = ' + wall3Th + ' cm' + '\n' +
                'Outer roof material: ' + roof1Type + ', thickness = ' + roof1Th + ' cm' + '\n' +
                'Middle roof material: ' + roof2Type + ', thickness = ' + roof2Th + ' cm' + '\n' +
                'Inner roof material: ' + roof3Type + ', thickness = ' + roof3Th + ' cm' + '\n' +
                # 'More?....' + '\n' +
                ' '  + '\n' +
                'ASSOCIATED PAVED TYPE:' + '\n' +
                'Name: ' + db_dict['NonVeg'].loc[PavedID]['Name'] + '\n' +
                'Origin: ' + db_dict['NonVeg'].loc[PavedID]['Origin'] + '\n' +
                'Mean albedo (min): ' + str(round(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[PavedID]['Albedo']]['Alb_min'].item(), 2)) + '\n' +
                'Mean albedo (max): ' + str(round(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[PavedID]['Albedo']]['Alb_min'].item(), 2)) + '\n' +
                'Effective Surface Emissivity: ' + str(round(db_dict['Emissivity'].loc[db_dict['NonVeg'].loc[PavedID]['Emissivity']]['Emissivity'].item(), 2))
         
                )
            
            if typology_sel['Url'].item() == None:
                dlg.label_2.clear()
            else:
                setup_image(dlg.label_2, typology_sel['Url'].item(), typology_sel['imageSource'].item())

    def setup_image(widget, url, imageSource):
        # if math.isnan(url):
            # widget.clear()
        # else:
        if type(url) == str:
            if imageSource != None:
                dlg.textBrowser_source.setText('Picture Author:, '+  str(imageSource))
                

            req = urllib.request.Request(str(url))
            try:
                resp = urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    QgsMessageLog.logMessage("Image URL encountered a 404 problem", level=Qgis.Critical)
                    widget.clear()
                else:
                    QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
                    widget.clear()
            except urllib.error.URLError as e:
                QgsMessageLog.logMessage("SUEWSPrepare encountered a problem: " + str(e), level=Qgis.Critical)
                widget.clear()
            else:
                data = resp.read()
                image = QImage()
                image.loadFromData(data)

                widget.setPixmap(QPixmap(image).scaledToWidth(450))

        else:
            widget.clear()
            dlg.textBrowser_source.setText('Picture Author missing')
            widget.setText('No example picture available in database')
    
    def generate_type():

        dict_reclass = {
            'ID' : create_code('Name'), #str('Type' + str(int(round(time.time())))),
            'Origin' : str(dlg.textEditOrig.value()),
            'Name' : str(dlg.textEditName.value()),
            'Description': str(dlg.textEditDesc.value()),
            'ProfileType' : dlg.comboBoxProf.currentText(),
            'Period' : dlg.comboBoxPeriod.currentText(),
            'Author' : str(dlg.textEditAuthor.value()),
            'Url' : nan, 
        }

        cbox_list = [dlg.comboBoxPavedType, dlg.comboBoxBuildingType]#, dlg.comboBoxGrassType, dlg.comboBoxDecType, dlg.comboBoxEvrType,dlg.comboBoxBsoilType, dlg.comboBoxWaterType]
        textbrowser_list = [dlg.textBrowser_0, dlg.textBrowser_1]#, dlg.textBrowser_2, dlg.textBrowser_3, dlg.textBrowser_4, dlg.textBrowser_5, dlg.textBrowser_6]
        

        for cbox, textbrowser in zip(cbox_list, textbrowser_list):

            var = textbrowser.toPlainText() # Paved or Buildings
            surf_table = db_dict['NonVeg'][db_dict['NonVeg']['Surface'] == var]
            dict_reclass[var] = surf_table[surf_table['nameOrigin'] == cbox.currentText()].index.item()

        new_edit = DataFrame.from_dict([dict_reclass]).set_index('ID')
        db_dict['Types'] = concat([db_dict['Types'], new_edit])
    
        save_to_db(db_path, db_dict)
        fill_cbox()

        QMessageBox.information(None, 'Sucessful','Database Updated')

    # def surface_info_changed(self):
    #     # TODO Update this. Outdated at the moment
    #     # Clear and enable ComboBox
    #     dlg.comboBoxElementInfo.clear()
    #     dlg.comboBoxElementInfo.setEnabled(True)
    #     # Read what surface user has chosen
    #     surface = dlg.comboBoxSurface.currentText()

    #     # Select correct tab fom DB (Veg, db_dict['NonVeg'] or Water)
    #     if surface == 'Paved' or surface == 'Buildings' or surface == 'Bare Soil':
    #         item_list = db_dict['NonVeg']['Name'][db_dict['NonVeg']['Surface'] == surface].tolist()
    #         origin = db_dict['NonVeg']['Origin'][db_dict['NonVeg']['Surface'] == surface].tolist()
    #         clr = db_dict['NonVeg']['Color'][db_dict['NonVeg']['Surface'] == surface].tolist()

    #         app_list = []
    #         for item, origin, clr in zip(item_list, origin, clr):
    #             # Join type and origin to present for user
    #             app_list.append((clr + ' ' + item + ', ' + origin))

    #     elif surface == 'Water':
    #         item_list = db_dict['NonVeg']['Name'][db_dict['NonVeg']['Surface'] == surface].tolist()
    #         origin = db_dict['NonVeg']['Origin'][db_dict['NonVeg']['Surface'] == surface].tolist()

    #         app_list = []
    #         for i, j in zip(item_list, origin):
    #             # Join type and origin to present for user
    #             app_list.append((i + ', ' + j))

    #     else: 
    #         item_list = db_dict['Veg']['Name'][db_dict['Veg']['Surface'] == surface].tolist()
    #         origin = db_dict['Veg']['Origin'][db_dict['Veg']['Surface'] == surface].tolist()

    #         app_list = []
    #         for i, j in zip(item_list, origin):
    #             # Join type and origin to present for user
    #             app_list.append((i + ', ' + j))

    #     dlg.comboBoxElementInfo.addItems(app_list)
    
    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 1:
            fill_cbox()
        dlg.label_2.clear()

    def to_type_edit():
        self.dlg.tabWidget.setCurrentIndex(2)
    
    # def to_element_edit():
    #     self.dlg.tabWidget.setCurrentIndex(2)
    
    self.dlg.tabWidget.currentChanged.connect(tab_update)
    dlg.editTypeButton.clicked.connect(to_type_edit)
    dlg.comboBoxTableSelect.currentIndexChanged.connect(changed)
    # dlg.comboBoxSurface.currentIndexChanged.connect(surface_info_changed)
    dlg.pushButtonCheck.clicked.connect(check_type)
    dlg.pushButtonGen.clicked.connect(generate_type)
    # dlg.pushButtonEditElement.clicked.connect(to_element_edit)
    dlg.comboBoxTableSelect.currentIndexChanged.connect(typology_info)
    

