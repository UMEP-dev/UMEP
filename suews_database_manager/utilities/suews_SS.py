#################################################################################################
#                                                                                               #
#                                  Spartacus Surface Creator                                    #
#                                                                                               #
#################################################################################################
from pandas import DataFrame, concat
from numpy import isnan, nan
from .database_functions import create_code, save_to_db, ref_changed
from qgis.PyQt.QtWidgets import QMessageBox

def setup_SUEWS_SS_creator(self, dlg, db_dict, db_path):

    def fill_cboxes():

        dlg.textEditName.clear()
        dlg.textEditOrig.clear()

        surf_table = db_dict['Spartacus Surface']
        surf_list = list(surf_table['nameOrigin'])
        dlg.comboBoxBase.clear()
        dlg.comboBoxBase.addItems(surf_list) 
        dlg.comboBoxBase.setCurrentIndex(-1)

        dlg.comboBoxRef.addItems(sorted(db_dict['References']['authorYear'])) 
        dlg.comboBoxRef.setCurrentIndex(-1)
    
        mat_list = list(db_dict['Spartacus Material']['nameOrigin'])
        mat_list.sort()
        mat_list.insert(0,'None')

        for roofwall in ['r', 'w']:
            for layer in range(1,6): #6 #TODO Change 4->6 if we want all 5 layers
                cbox = getattr(dlg, f'comboBox_{roofwall}{str(layer)}', None)
            
                cbox.clear()
                cbox.addItems(mat_list)

                lineEdit = getattr(dlg, f'lineEdit_{roofwall}{str(layer)}', None)
                lineEdit.setText('')
        
    def print_table(dlg, idx, rw):
        try:
            # Print texts for selected material in textBrowser for selected layer
            Tb = getattr(dlg, 'textBrowser_' + rw + str(idx))       # Textbrowser 
            mat_cbox = getattr(dlg, 'comboBox_' + rw + str(idx))    # Material combobox
            material = mat_cbox.currentText()                   # Selected material

            if material != 'None':
                
                mat_table = db_dict['Spartacus Material']                   # Set correct table from db
                material_sel = mat_table[mat_table['nameOrigin'] == material]   # Slice correct material from table

                Tb.setText(                                             # Write texts of the selected material in the textbrowser
                    'Albedo: ' + str(material_sel['Albedo'].item()) + '\n' + 
                    'Emissivity: ' + str(material_sel['Emissivity'].item()) + '\n' +
                    'Thermal Conductivity: ' + str(material_sel['Thermal Conductivity'].item()) + '\n' +
                    'Specific Heat Capacity: ' + str(material_sel['Specific Heat'].item()) + '\n' 
                )
                # activate frames of following layer.
                if idx <6:
                    frame_plus = getattr(dlg,f'frame_{rw}{str(idx+1)}')
                    frame_plus.setEnabled(True)    
            else:
                # if material set to None, just clean the text Browser
                Tb.setText('')
                if idx <6:
                    frame_plus = getattr(dlg,f'frame_{rw}{str(idx+1)}')
                    frame_plus.setEnabled(False) 
        except:
            pass

    def new_edit():

        spartacus_dict = {}
        # Roof ##########################

        # roof and wall comboboxes
        r1_mat = dlg.comboBox_r1.currentText()
        r2_mat = dlg.comboBox_r2.currentText()
        r3_mat = dlg.comboBox_r3.currentText()
        r4_mat = dlg.comboBox_r4.currentText()
        r5_mat = dlg.comboBox_r5.currentText()

        w1_mat = dlg.comboBox_w1.currentText()
        w2_mat = dlg.comboBox_w2.currentText()
        w3_mat = dlg.comboBox_w3.currentText()
        w4_mat = dlg.comboBox_w4.currentText()
        w5_mat = dlg.comboBox_w5.currentText()
        
        mat_table = db_dict['Spartacus Material']

        for cols in db_dict['Spartacus Surface'].columns:
            if cols != 'nameOrigin':
                spartacus_dict[cols] = nan
        
        spartacus_dict['ID'] = create_code('Spartacus Surface')
        spartacus_dict['Name'] = str(dlg.textEditName.value())
        spartacus_dict['Origin'] = str(dlg.textEditOrig.value())
        spartacus_dict['Ref'] = db_dict['References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item() 

        # Roof 
        if r1_mat != 'None':
            spartacus_dict['r1Material'] = mat_table[mat_table['nameOrigin'] == r1_mat].index.item()
            spartacus_dict['r1Thickness'] = float(dlg.lineEdit_r1.text())
            if r2_mat != 'None':
                spartacus_dict['r2Material'] = mat_table[mat_table['nameOrigin'] == r2_mat].index.item()
                spartacus_dict['r2Thickness'] = float(dlg.lineEdit_r2.text())
                if r3_mat != 'None':
                    spartacus_dict['r3Material'] = mat_table[mat_table['nameOrigin'] == r3_mat].index.item()
                    spartacus_dict['r3Thickness'] = float(dlg.lineEdit_r3.text())
                    if r4_mat != 'None':
                        spartacus_dict['r4Material'] = mat_table[mat_table['nameOrigin'] == r4_mat].index.item()
                        spartacus_dict['r4Thickness'] = float(dlg.lineEdit_r4.text())
                        if r5_mat != 'None':
                            spartacus_dict['r5Material'] = mat_table[mat_table['nameOrigin'] == r5_mat].index.item()
                            spartacus_dict['r5Thickness'] = float(dlg.lineEdit_r5.text())
                        else:
                            pass
                    else:
                        pass
                else:
                    pass   
            else:
                pass    
        # Wall 
        if w1_mat != 'None':
            spartacus_dict['w1Material'] = mat_table[mat_table['nameOrigin'] == w1_mat].index.item()
            spartacus_dict['w1Thickness'] = float(dlg.lineEdit_w1.text())
            if w2_mat != 'None':
                spartacus_dict['w2Material'] = mat_table[mat_table['nameOrigin'] == w2_mat].index.item()
                spartacus_dict['w2Thickness'] = float(dlg.lineEdit_w2.text())
                if w3_mat != 'None':
                    spartacus_dict['w3Material'] = mat_table[mat_table['nameOrigin'] == w3_mat].index.item()
                    spartacus_dict['w3Thickness'] = float(dlg.lineEdit_w3.text())
                    if w4_mat != 'None':
                        spartacus_dict['w4Material'] = mat_table[mat_table['nameOrigin'] == w4_mat].index.item()
                        spartacus_dict['w4Thickness'] = float(dlg.lineEdit_w4.text())
                        if w5_mat != 'None':
                            spartacus_dict['w5Material'] = mat_table[mat_table['nameOrigin'] == w5_mat].index.item()
                            spartacus_dict['w5Thickness'] = float(dlg.lineEdit_w5.text())
                        else:
                            pass
                    else:
                        pass
                else:
                    pass   
            else:
                pass 

        # for i in [1,2,3,4,5]:
        #     r_insulation = eval('dlg.radioButton_r' + str(i))
        #     w_insulation = eval('dlg.radioButton_w' + str(i))
        #     if r_insulation.isChecked() == True:
        #         spartacus_dict['rInsulation'] = i
            
        #     if w_insulation.isChecked() == True:
        #         spartacus_dict['wInsulation'] = i
        
        # print(spartacus_dict)
                
        new_edit = DataFrame([spartacus_dict]).set_index('ID')
        db_dict['Spartacus Surface'] = concat([db_dict['Spartacus Surface'], new_edit])
        save_to_db(db_path, db_dict)

        QMessageBox.information(None, 'Succesful', f'New edit {spartacus_dict['Name']}, {spartacus_dict['Origin']} added to your local database')
        fill_cboxes()
              
    def base_surface_changed():

        spartacus_str = dlg.comboBoxBase.currentText()

        if dlg.comboBoxBase.currentIndex() != -1: 
            surf_table = db_dict['Spartacus Surface']
            mat_table = db_dict['Spartacus Material']

            spartacus_sel = surf_table[surf_table['nameOrigin'] == spartacus_str]

            mat_list = list(db_dict['Spartacus Material']['nameOrigin'])
            mat_list.sort()
            mat_list.insert(0,'None')
            
            for roofwall in ['r', 'w']:
                for layer in range(1,6): #6 #TODO Change 4->6 if we want all 5 layers
                    cbox = getattr(dlg, f'comboBox_{roofwall}{str(layer)}', None)
                    lineEdit = getattr(dlg, f'lineEdit_{roofwall}{str(layer)}', None)

                    mat_idx = spartacus_sel.loc[:,(roofwall + str(layer) + 'Material')].item()

                    if isnan(mat_idx) != True:
                        material = mat_table.loc[mat_idx, 'nameOrigin']
                        mat_table.loc[mat_idx, 'nameOrigin']
                        cbox_index = mat_list.index(material)
                        cbox.setCurrentIndex(cbox_index)
                        thickness = spartacus_sel.loc[:,(roofwall + str(layer) + 'Thickness')].item()
                        lineEdit.setText(str(thickness))                   
                    else:
                        cbox.setCurrentIndex(cbox.findText('None'))
                        lineEdit.clear()
                        # set correct ref
            try:
                ref_id = spartacus_sel['Ref']
                ref_index = db_dict['References'].loc[ref_id, 'authorYear'].item()
                dlg.comboBoxRef.setCurrentIndex(dlg.comboBoxRef.findText(ref_index))
            except:
                dlg.comboBoxRef.setCurrentIndex(-1) 


            # wInsulation = spartacus_sel['wInsulation'].item()
            # w_insulation = eval('dlg.radioButton_w' + str(wInsulation))
            # w_insulation.setChecked(True)s

            # rInsulation = spartacus_sel['rInsulation'].item()
            # r_insulation = eval('dlg.radioButton_r' + str(rInsulation))
            # r_insulation.setChecked(True)

        else:
            pass

    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 8:
            fill_cboxes()

    dlg.comboBoxRef.currentIndexChanged.connect(lambda: ref_changed(dlg, db_dict))    
    dlg.pushButtonGen.clicked.connect(new_edit)
    dlg.comboBoxBase.currentIndexChanged.connect(base_surface_changed)
    dlg.comboBox_r1.currentIndexChanged.connect(lambda: print_table(dlg,1,'r'))
    dlg.comboBox_r2.currentIndexChanged.connect(lambda: print_table(dlg,2,'r'))
    dlg.comboBox_r3.currentIndexChanged.connect(lambda: print_table(dlg,3,'r'))
    dlg.comboBox_r4.currentIndexChanged.connect(lambda: print_table(dlg,4,'r'))
    dlg.comboBox_r5.currentIndexChanged.connect(lambda: print_table(dlg,5,'r'))
    dlg.comboBox_w1.currentIndexChanged.connect(lambda: print_table(dlg,1,'w'))
    dlg.comboBox_w2.currentIndexChanged.connect(lambda: print_table(dlg,2,'w'))
    dlg.comboBox_w3.currentIndexChanged.connect(lambda: print_table(dlg,3,'w'))
    dlg.comboBox_w4.currentIndexChanged.connect(lambda: print_table(dlg,4,'w'))
    dlg.comboBox_w5.currentIndexChanged.connect(lambda: print_table(dlg,5,'w'))
    # self.dlg.tabWidget.tabBarClicked.connect(fill_cboxes)
    self.dlg.tabWidget.currentChanged.connect(tab_update)
    
    # dlg.comboBoxSurface.currentIndexChanged.connect(surface_changed)
    # dlg.comboBoxBaseESTM.currentIndexChanged.connect(base_ETSM_changed)
    # dlg.pushButtonToRefManager.clicked.connect(self.to_ref)