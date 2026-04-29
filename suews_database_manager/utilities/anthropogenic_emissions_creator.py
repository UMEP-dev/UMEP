from pandas import DataFrame, concat
from .database_functions import save_to_db, create_code, ref_changed
from qgis.PyQt.QtWidgets import QMessageBox


#################################################################################################
#                                                                                               #
#                                  Antrhopogenic Emission Manager                               #
#                                                                                               #
#################################################################################################

def setup_anthropogenic_emission_manager(self, dlg, db_dict, db_path):
    
    def fill_cboxes():

        dlg.comboBoxBaseAnEm.clear()
        dlg.comboBoxBaseAnEm.addItems(db_dict['AnthropogenicEmission']['nameOrigin'].tolist())
        dlg.comboBoxBaseAnEm.setCurrentIndex(-1)
        dlg.comboBoxRef.addItems(sorted(db_dict['References']['authorYear'])) 
        dlg.comboBoxRef.setCurrentIndex(-1)
        dlg.comboBoxModel.setCurrentIndex(-1)

        for i in range(1,18):
            Le = getattr(dlg, f'lineEdit_{i}')
            Le.clear()

        dlg.textEditName.clear()
        dlg.textEditOrig.clear()
        
    def base_AnEm_changed():

        if dlg.comboBoxBaseAnEm.currentIndex() != -1: 
            base_irr = dlg.comboBoxBaseAnEm.currentText()
            AnEm_sel = db_dict['AnthropogenicEmission'][db_dict['AnthropogenicEmission']['nameOrigin'] == base_irr]

            AnEm_sel_dict = AnEm_sel.squeeze().to_dict()        
            for i in range(1,18):
                Tb = getattr(dlg, f'textBrowser_{i}')
                Le = getattr(dlg, f'lineEdit_{i}')
                Le.clear()
                Le.setText(str(AnEm_sel_dict[Tb.toPlainText()]))

            # set correct ref
            try:
                ref_id = AnEm_sel['Ref']
                ref_index = db_dict['References'].loc[ref_id, 'authorYear'].item()
                dlg.comboBoxRef.setCurrentIndex(dlg.comboBoxRef.findText(ref_index))
            except:
                dlg.comboBoxRef.setCurrentIndex(-1) 

            # Set crrect model
            try:
                model_index = dlg.comboBoxModel.findText(str(AnEm_sel['Model'].item()))
                dlg.comboBoxModel.setCurrentIndex(model_index)
            except:
                dlg.comboBoxModel.setCurrentIndex(-1)

    
    def model_changed():
        model = dlg.comboBoxModel.currentText()

        if model == str(2):
            for i in range(7,18):   
                Tb = getattr(dlg, f'textBrowser_{i}')
                Le = getattr(dlg, f'lineEdit_{i}')
                Tb.setDisabled(True)
                Le.setDisabled(True)
                Le.clear()
        elif model == str(4):
            for i in range(7,18):   
                Tb = getattr(dlg, f'textBrowser_{i}')
                Le = getattr(dlg, f'lineEdit_{i}')
                Tb.setEnabled(True)
                Le.setEnabled(True)
        else:
            pass       


    def add_AnEm():

        dict_reclass = {
            'ID' : create_code('AnthropogenicEmission'),
            'Name' : dlg.textEditName.value(),
            'Origin' : dlg.textEditOrig.value(),
        }
        
        for i in range(1,18):
            Tb = getattr(dlg, f'textBrowser_{i}')
            Le = getattr(dlg, f'lineEdit_{i}')
            col = Tb.toPlainText()
            val = Le.text()
            dict_reclass[col] = val
        
        new_edit = DataFrame([dict_reclass]).set_index('ID')
        db_dict['AnthropogenicEmission'] = concat([db_dict['AnthropogenicEmission'], new_edit])

        save_to_db(db_path, db_dict)
        QMessageBox.information(None, 'Succesful', 'New edit added to your local database')
        fill_cboxes()


    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 4:
            fill_cboxes()

    def to_ref_edit():
        self.dlg.tabWidget.setCurrentIndex(10)

    dlg.pushButtonToRefManager.clicked.connect(to_ref_edit)
    dlg.pushButtonGen.clicked.connect(add_AnEm)
    dlg.comboBoxRef.currentIndexChanged.connect(lambda: ref_changed(dlg, db_dict))    
    dlg.comboBoxBaseAnEm.currentIndexChanged.connect(base_AnEm_changed)
    dlg.comboBoxModel.currentIndexChanged.connect(model_changed)
    self.dlg.tabWidget.currentChanged.connect(tab_update)
    


    

