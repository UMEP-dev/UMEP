from pandas import DataFrame, concat
from qgis.PyQt.QtWidgets import QMessageBox
from .database_functions import create_code, save_to_db, ref_changed

def setup_SS_material_creator(self, dlg, db_dict, db_path):

    def start_material_creator(dlg):

        dlg.comboBoxBase.clear()
        dlg.comboBoxBase.addItems(sorted(db_dict['Spartacus Material']['nameOrigin'])) 
        dlg.comboBoxBase.setCurrentIndex(-1)
        
        dlg.comboBoxRef.clear()
        dlg.comboBoxRef.addItems(sorted(db_dict['References']['authorYear'])) 
        dlg.comboBoxRef.setCurrentIndex(-1)

        dlg.textEditName.clear()
        dlg.textEditColor.clear()
        dlg.textEditOrig.clear()
        dlg.textEditAlbedo.clear()
        dlg.textEditEmissivity.clear()
        dlg.textEditThermalC.clear()
        dlg.textEditSpecificH.clear()

    def generate_material():

        dict_reclass = {
            'ID' : create_code('Spartacus Material'), 
            'Name' : str(dlg.textEditName.value()),
            'Color' : str(dlg.textEditColor.value()),
            'Origin': str(dlg.textEditOrig.value()),
            'Albedo': float((dlg.textEditAlbedo.value())),
            'Emissivity' : float((dlg.textEditEmissivity.value())),
            'Thermal Conductivity': float((dlg.textEditThermalC.value())),
            'Specific Heat': float((dlg.textEditSpecificH.value())),
            'Ref' : (db_dict['References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item() )
        }

        new_edit = DataFrame([dict_reclass]).set_index('ID')
        db_dict['Spartacus Material'] = concat([db_dict['Spartacus Material'], new_edit])

        save_to_db(db_path, db_dict)

        QMessageBox.information(None, 'Succesful', 'New edit added to your local database')
        start_material_creator(dlg) # Clear tab

    def base_changed():
        
        base_str = dlg.comboBoxBase.currentText()
        if base_str != '': 
            
            base = db_dict['Spartacus Material'].loc[db_dict['Spartacus Material']['nameOrigin'] == base_str]

            dlg.textEditAlbedo.setValue(str(base['Albedo'].item()))
            dlg.textEditEmissivity.setValue(str(base['Emissivity'].item()))
            dlg.textEditThermalC.setValue(str(base['Thermal Conductivity'].item()))
            dlg.textEditSpecificH.setValue(str(base['Specific Heat'].item()))

            try:        
                ref_id = base['Ref']
                ref_index = db_dict['References'].loc[ref_id, 'authorYear'].item()
                dlg.comboBoxRef.setCurrentIndex(dlg.comboBoxRef.findText(ref_index))
            except:
                dlg.comboBoxRef.setCurrentIndex(-1)
                print(ref_id)


    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 9:
            start_material_creator(dlg)

    def to_ref_edit():
        self.dlg.tabWidget.setCurrentIndex(10)

    dlg.comboBoxRef.currentIndexChanged.connect(lambda: ref_changed(dlg, db_dict))    
    dlg.pushButtonToRefManager.clicked.connect(to_ref_edit)
    self.dlg.tabWidget.currentChanged.connect(tab_update)
    dlg.pushButtonGen.clicked.connect(generate_material)
    dlg.comboBoxBase.currentIndexChanged.connect(base_changed)
