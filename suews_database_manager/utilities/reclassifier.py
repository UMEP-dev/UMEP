#################################################################################################
#                                                                                               #
#                                        Main tab - Reclassifier                                #
#                                                                                               #
#################################################################################################

from pathlib import Path
from .database_functions import save_to_db

from qgis.PyQt.QtCore import  QVariant
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import QgsVectorLayer, QgsMapLayerProxyModel, QgsProject, QgsField, QgsVectorFileWriter

def setup_reclassifier(self, dlg, db_dict):

    def fill_cbox():
        dlg.comboBoxNew1.clear()        

        typology_list = list(db_dict['Types']['nameOrigin'])
        for i in range(1, 23):
            Nc = getattr(dlg, f'comboBoxNew{i}')
            Nc.addItems(typology_list)
            Nc.setCurrentIndex(-1)
            Nc.setDisabled(True)
            vars()[f'dlg.comboBoxNew{i}'] = Nc

    def field_changed():

        layer = self.layerComboManagerPoint.currentLayer()

        if not layer:
            return

        att_list = [field.name() for field in layer.fields()]
        att_column = dlg.comboBoxField.currentText()

        if not att_column:
            return

        try:
            att_index = att_list.index(att_column)
        except ValueError:
            return

        unique_values = list(layer.uniqueValues(att_index))
        len_uv = len(unique_values)

        # Ensure always String 
        unique_values = [str(x) for x in unique_values]

        for i in range(1, 23):
            # Oc == Old Class
            Oc = getattr(dlg, f'comboBoxClass{i}')
            Oc.clear()
            Oc.setDisabled(True)
            vars()[f'dlg.comboBoxClass{i}'] = Oc
            
            # Nc == New Class
            Nc = getattr(dlg, f'comboBoxNew{i}')
            Nc.setCurrentIndex(-1)
            Nc.setDisabled(True)
            vars()[f'dlg.comboBoxNew{i}'] = Nc

        for i in range(min(len_uv, 22)):
            idx = i + 1
            
            # Oc == Old Class
            Oc = getattr(dlg, f'comboBoxClass{idx}')
            Oc.addItems(unique_values)
            Oc.setCurrentIndex(i)
            vars()[f'dlg.comboBoxClass{idx}'] = Oc

            # Nc == New Class
            Nc = getattr(dlg, f'comboBoxNew{idx}')
            Nc.setEnabled(True)
            vars()[f'dlg.comboBoxNew{idx}'] = Nc

    def layer_changed():

        try:
            layer = self.layerComboManagerPoint.currentLayer()
            att_list = list(layer.attributeAliases())
            dlg.comboBoxField.clear()
            dlg.comboBoxField.setEnabled(True)
            dlg.comboBoxField.addItems(att_list)
            dlg.comboBoxField.setCurrentIndex(0)

            field_changed() 
        except:
            pass
        
    # def typology_info():
    #     typology_str = dlg.comboBoxType.currentText()
    #     dlg.textBrowser.clear()
    #     if dlg.comboBoxType.currentIndex() != -1:
    #         #typology_sel = db_dict['NonVeg'].loc[db_dict['NonVeg']['nameOrigin'] == typology_str]
    #         typology_sel = db_dict['Types'].loc[db_dict['Types']['nameOrigin'] == typology_str]
    #         buildID = typology_sel['Buildings'].item()
    #         PavedID  = typology_sel['Paved'].item()

    #         dlg.textBrowser.setText(
    #             'URBAN TYPOLOGY:' + '\n' +
    #             'Typology: ' + typology_sel['Name'].item() + '\n' +
    #             'Origin: ' + typology_sel['Origin'].item() + '\n' +
    #             'Construction perion: ' +  typology_sel['Period'].item() + '\n' +
    #             ' '  + '\n' +
    #             'ASSOCIATED BUILDING TYPE:' + '\n' +
    #             'Name: ' + db_dict['NonVeg'].loc[buildID]['Name'] + '\n' +
    #             'Origin: ' + db_dict['NonVeg'].loc[buildID]['Origin'] + '\n' +
    #             'Bulk albedo (min): ' + str(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[buildID]['Albedo']]['Alb_min'].item()) + '\n' +
    #             'Bulk albedo (max): ' + str(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[buildID]['Albedo']]['Alb_min'].item()) + '\n' +
    #             'Effective Surface Emissivity: ' + str(db_dict['Emissivity'].loc[db_dict['NonVeg'].loc[buildID]['Emissivity']]['Emissivity'].item()) + '\n' +
    #             'U-value (roof): ' + str(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID]['Spartacus Surface']]['u_value_roof']) + '\n' +
    #             'U-value (walls): ' + str(db_dict['Spartacus Surface'].loc[db_dict['NonVeg'].loc[buildID]['Spartacus Surface']]['u_value_wall']) + '\n' +
    #             'More?....' + '\n' +
    #             ' '  + '\n' +
    #             'ASSOCIATED PAVED TYPE:' + '\n' +
    #             'Name: ' + db_dict['NonVeg'].loc[PavedID]['Name'] + '\n' +
    #             'Origin: ' + db_dict['NonVeg'].loc[PavedID]['Origin'] + '\n' +
    #             'Bulk albedo (min): ' + str(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[PavedID]['Albedo']]['Alb_min'].item()) + '\n' +
    #             'Bulk albedo (max): ' + str(db_dict['Albedo'].loc[db_dict['NonVeg'].loc[PavedID]['Albedo']]['Alb_min'].item()) + '\n' +
    #             'Effective Surface Emissivity: ' + str(db_dict['Emissivity'].loc[db_dict['NonVeg'].loc[PavedID]['Emissivity']]['Emissivity'].item()) + '\n' +
    #             'More?....'
    #             )
        
    def savefile():
        # Add possibilites to save as other format? Is .shp only format used in SUEWS Prepare?
        self.outputfile = self.fileDialog.getSaveFileName(None, 'Save File As:', None, 'Shapefiles (*.shp)')
        dlg.textOutput.setText(self.outputfile[0])

    def backupDatabase():
        # Add possibilites to save as other format? Is .shp only format used in SUEWS Prepare?
        self.backupPath = self.fileDialog.getSaveFileName(None, 'Save File As:', None, 'Excel (*.xlsx)')
        save_to_db(self.backupPath[0], db_dict)
        QMessageBox.information(None, 'Export Complete', 'Help others and share your data by submitting your database to our UMEP GitHub. See help for more info.')
        # update_db(db_dict, db_path, updated_db_path, backup_path)
        # dlg.textOutput.setText(self.outputfile[0])

    def start_progress():

        vlayer = self.layerComboManagerPoint.currentLayer()
        att_list = []

        QgsVectorFileWriter.writeAsVectorFormat(vlayer, dlg.textOutput.text(), "UTF-8", vlayer.crs(), "ESRI Shapefile")
        vlayer = QgsVectorLayer(self.outputfile[0], Path(self.outputfile[0]).name[:-4])

        for fieldName in vlayer.fields():
            att_list.append(fieldName.name())

        att_column = dlg.comboBoxField.currentText() # Selected columns in  vectorlayer
        att_index = att_list.index(att_column)
        
        unique_values = list(vlayer.uniqueValues(att_index))
        
        dict_reclass = {}       # dict for reclassifying typologynames as string
        dict_reclassID = {}     # dict for reclassifying typologyID as integer

        idx = 1
        for i in range(len(unique_values)):  
            if idx > 13:
                break
            
            # Left side
            Oc = getattr(dlg, f'comboBoxClass{idx}')
            oldField = Oc.currentText()
            
            # Right side
            Nc = getattr(dlg, f'comboBoxNew{idx}')
            newField = Nc.currentText()
            
            dict_reclass[str(oldField)] = str(newField)
            dict_reclassID[str(oldField)] = db_dict['Types'].loc[db_dict['Types']['nameOrigin'] == str(newField)].index.item()
            
            idx += 1

        newFieldName = 'TypolName' # New field for typology name
        newFieldID = 'TypolID'   # New field for typologyID

        # Add fields in vectorlayer
        fields = [
            QgsField(newFieldName, QVariant.String),
            QgsField(newFieldID, QVariant.Int),
        ]

        vlayer.startEditing()
        vlayer.dataProvider().addAttributes(fields)
        vlayer.updateFields()
        
        # Reclassify new fields using reclassify dictionaries created above
        for feature in vlayer.getFeatures():
            old_value = feature[att_column] 
            new_value1 = dict_reclass.get(old_value, None)
            new_value2 = dict_reclassID.get(old_value, None)
            
            if new_value1 is not None:
                feature[newFieldName] = new_value1
            if new_value2 is not None:
                feature[newFieldID] = new_value2
            
            vlayer.updateFeature(feature)

        vlayer.commitChanges()

        QgsProject.instance().addMapLayer(vlayer) # Add vectorlayer to QGIS-project

        QMessageBox.information(None, 'Process Complete', 'Your reclassified shapefile has been added to project. Proceed to SUEWS Preprare Database Typologies')
        dlg.textOutput.clear()


    self.layerComboManagerPoint = dlg.comboBoxVector
    self.layerComboManagerPoint.setCurrentIndex(-1)
    self.layerComboManagerPoint.setFilters(QgsMapLayerProxyModel.PolygonLayer)

    fill_cbox()

    dlg.comboBoxVector.currentIndexChanged.connect(layer_changed)
    dlg.comboBoxField.currentIndexChanged.connect(field_changed)

    self.fileDialog = QFileDialog()
    dlg.pushButtonSave.clicked.connect(savefile)
    
    # Set up for the run button
    dlg.runButton.clicked.connect(start_progress)

    dlg.pushButtonUpdateDatabase.clicked.connect(backupDatabase)

    
        
