from pandas import DataFrame, concat
from .database_functions import save_to_db, create_code, ref_changed
from qgis.PyQt.QtWidgets import QMessageBox

#################################################################################################
#                                                                                               #
#                                  Irrigation manager                                           #
#                                                                                               #
#################################################################################################


def setup_irrigation_manager(self, dlg, db_dict, db_path):

    def fill_cboxes():
        dlg.comboBoxBaseIrr.clear()
        dlg.comboBoxRef.clear()
        dlg.textEditName.clear()
        dlg.textEditOrig.clear()
        
        for i in range(0,25):
            Le = getattr(dlg, f'IrrLineEdit_{i}', None)
            Le.clear()
    
        dlg.comboBoxBaseIrr.addItems(db_dict['Irrigation']['nameOrigin'].tolist())
        dlg.comboBoxBaseIrr.setCurrentIndex(-1)
        dlg.comboBoxRef.addItems(sorted(db_dict['References']['authorYear'])) 
        dlg.comboBoxRef.setCurrentIndex(-1)

    def base_irr_changed():
        base_irr = dlg.comboBoxBaseIrr.currentText()
        irr_sel = db_dict['Irrigation'][db_dict['Irrigation']['nameOrigin'] == base_irr]

        irr_sel_dict = irr_sel.squeeze().to_dict()

        for i in range(0,25):
            Tb = getattr(dlg, f'textBrowser_{i}', None)
            Le = getattr(dlg, f'IrrLineEdit_{i}', None)
            Le.clear()
            Le.setText(str(irr_sel_dict[Tb.toPlainText()]))

        # set correct ref
        try:
            ref_id = irr_sel['Ref']
            ref_index = db_dict['References'].loc[ref_id, 'authorYear'].item()
            dlg.comboBoxRef.setCurrentIndex(dlg.comboBoxRef.findText(ref_index))
        except:
            dlg.comboBoxRef.setCurrentIndex(-1) 

    def add_irr():

        # refindex = db_dict['References'].copy()
        # refindex['authorYear'] = (refindex['Author'] + ' ,(' + refindex['Publication Year'].apply(str) + ')')
        dict_reclass = {
            'ID' : create_code('Irrigation'),
            'Name' : dlg.textEditName.value(),
            'Origin' : dlg.textEditOrig.value(),
            'Ref' : db_dict['References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item() 
        }

        for i in range(0, 25): 
            Tb = getattr(dlg, f'textBrowser_{i}', None)
            Le = getattr(dlg, f'IrrLineEdit_{i}', None)
            col = Tb.toPlainText()
            val = Le.text()
            dict_reclass[col] = val

        new_edit = DataFrame([dict_reclass]).set_index('ID')
        db_dict['Irrigation'] = concat([db_dict['Irrigation'], new_edit])
        save_to_db(db_path, db_dict)

        QMessageBox.information(None, 'Succesful', 'Irrigation Entry added to your local database')
        fill_cboxes()

    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 6:
            fill_cboxes()
    
    self.dlg.tabWidget.currentChanged.connect(tab_update)

    dlg.comboBoxRef.currentIndexChanged.connect(lambda: ref_changed(dlg, db_dict))    
    dlg.comboBoxBaseIrr.currentIndexChanged.connect(base_irr_changed)
    dlg.pushButtonGen.clicked.connect(add_irr)