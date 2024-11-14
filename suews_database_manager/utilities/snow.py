from pandas import DataFrame, concat
from .database_functions import save_to_db, create_code, ref_changed
from qgis.PyQt.QtWidgets import QMessageBox

#################################################################################################
#                                                                                               #
#                                  Snow Creator                                                 #
#                                                                                               #
#################################################################################################
def setup_snow_creator(self, dlg, db_dict, db_path ):
    
    # Startup function, clean and setup
    def fill_cbox():
        dlg.comboBoxRef.clear()
        dlg.comboBoxRef.addItems(sorted(db_dict['References']['authorYear'])) 
        dlg.comboBoxRef.setCurrentIndex(-1)
        
        dlg.comboBoxBase.clear()
        dlg.comboBoxBase.addItems(db_dict['Snow']['nameOrigin'].tolist())
        dlg.comboBoxBase.setCurrentIndex(-1)

        dlg.textEditName.clear(),
        dlg.textEditOrig.clear()

        # Clear all LineEdits
        for i in range(0, 11): 
            Le = getattr(dlg, f'LineEdit_{i}')
            Le.clear()
        
        # Fill comboboxes with albedo, emissivity and OHM values 
        for i in range(0, 6): 
            Tb = getattr(dlg, f'textBrowserCb_{i}')
            Cb = getattr(dlg, f'comboBox_{i}')
   
            tablename = Tb.toPlainText()
            if tablename.startswith('OHM'):
                Cb.addItems(sorted(db_dict['OHM']['nameOrigin'][db_dict['OHM']['Surface'] == 'Snow'].tolist()))
            else:               
                Cb.addItems(sorted(db_dict[tablename]['nameOrigin'][db_dict[tablename]['Surface'] == 'Snow'].tolist()))
           
            Cb.setCurrentIndex(-1)

    def base_snow_changed():
        
        # Check if base is selected
        base_snow = dlg.comboBoxBase.currentText()

        if dlg.comboBoxBase.currentIndex() != -1:
            # slice dataframe for selected base snow
            snow_sel = db_dict['Snow'].loc[db_dict['Snow']['nameOrigin'] == base_snow]
            
            # Set LineEdits (text boxes) according to base snow
            for i in range(0, 11): 
                Tb = getattr(dlg, f'textBrowser_{i}')
                Le = getattr(dlg, f'LineEdit_{i}')
                Le.setText(str(snow_sel[Tb.toPlainText()].item()))

            # Set comboboxes according to base snow
        
            for i in range(0, 6): 
                Tb = getattr(dlg, f'textBrowserCb_{i}')
                Cb = getattr(dlg, f'comboBox_{i}')

                # use nameOrigin to locate correct index in combobox        
                tablename = Tb.toPlainText()
                if tablename.startswith('OHM'):
                    indexer = db_dict['OHM'].loc[snow_sel[tablename].item(), 'nameOrigin']
                else:
                    indexer = db_dict[tablename].loc[snow_sel[tablename].item(), 'nameOrigin']

                # set index in combobox
                Cb_index = Cb.findText(indexer)     
                Cb.setCurrentIndex(Cb_index)

            
            # set correct ref
            try:
                ref_id = snow_sel['Ref']
                ref_index = db_dict['References'].loc[ref_id, 'authorYear'].item()
                dlg.comboBoxRef.setCurrentIndex(dlg.comboBoxRef.findText(ref_index))
            except:
                dlg.comboBoxRef.setCurrentIndex(-1) 

    def add_snow():

        dict_reclass = {
            'ID' : create_code('Snow'),
            'Name' : dlg.textEditName.value(),
            'Origin' : dlg.textEditOrig.value(),
            'Ref' : db_dict['References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item() 
        }

        # read LineEdits (text boxes)
        for i in range(0, 11): 
            Tb = getattr(dlg, f'textBrowser_{i}')
            Le = getattr(dlg, f'LineEdit_{i}')
            dict_reclass[Tb.toPlainText] = float(Le.text())

        # Read comboboxes
        for i in range(0, 6): 
            Tb = getattr(dlg, f'textBrowserCb_{i}')
            Cb = getattr(dlg, f'comboBox_{i}')

            # use nameOrigin to locate Code            
            tablename = Tb.toPlainText()
            current_text = Cb.currentText()

            if tablename.startswith('OHM'):
                dict_reclass[Tb.toPlainText()] =  db_dict['OHM'].loc[db_dict['OHM']['nameOrigin'] == current_text].index.item()
            else:
                dict_reclass[Tb.toPlainText()] = db_dict[tablename].loc[db_dict[tablename]['nameOrigin'] == current_text].index.item()

        new_edit = DataFrame([dict_reclass]).set_index('ID')
        db_dict['Snow'] = concat([db_dict['Snow'], new_edit])
        save_to_db(db_path, db_dict)

        QMessageBox.information(None, 'Succesful', 'Snow Entry added to your local database')

        tab_update()


    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 7:
            fill_cbox()

    self.dlg.tabWidget.currentChanged.connect(tab_update)
    dlg.comboBoxRef.currentIndexChanged.connect(lambda: ref_changed(dlg, db_dict))    
    dlg.comboBoxBase.currentIndexChanged.connect(base_snow_changed)
    dlg.pushButtonGen.clicked.connect(add_snow) 