from qgis.PyQt.QtWidgets import QMessageBox
from pandas import DataFrame, concat
from .database_functions import create_code, save_to_db, surf_df_dict, get_combobox_items


#################################################################################################
#                                                                                               #
#                                  Land Cover Creator                                           #
#                                                                                               #
#################################################################################################

def setup_landcover_creator(self, dlg, db_dict, db_path):

    def fill_cbox():
        
        dlg.comboBoxSurface.blockSignals(True)

        dlg.textBrowserEl.clear()
        dlg.comboBoxProfileType.setCurrentIndex(-1)

        for i in range(20): 
            Oc = getattr(dlg, f'textBrowser_{i}', None)
            if Oc:
                Oc.clear()
                Oc.setDisabled(True)
            Nc = getattr(dlg, f'comboBox_{i}', None)
            if Nc:
                Nc.clear()
                Nc.setDisabled(True)        
            
        dlg.comboBoxBase.setCurrentIndex(-1)
        dlg.comboBoxSurface.setCurrentIndex(-1)
        
        dlg.textEditName.clear()
        dlg.textEditOrig.clear()
        dlg.comboBoxSurface.blockSignals(False)


    def changed_surface():

        dlg.comboBoxBase.blockSignals(True)

        dlg.comboBoxBase.clear()
        dlg.textEditName.clear()
        dlg.textEditOrig.clear()
        
        dlg.comboBoxBase.setEnabled(True)

        for i in range(20):
            Oc = getattr(dlg, f'textBrowser_{i}', None)
            if Oc:
                Oc.clear()
                Oc.setDisabled(True)
            Nc = getattr(dlg, f'comboBox_{i}', None)
            if Nc:
                Nc.clear()
                Nc.setDisabled(True)

        surface = dlg.comboBoxSurface.currentText()
        dlg.comboBoxProfileType.blockSignals(True)

        if surface:
            handle_surface_selection(surface)

        dlg.comboBoxProfileType.blockSignals(False)
        dlg.comboBoxBase.blockSignals(False)

    def handle_surface_selection(surface):

        # Deactivate  Changed function
        dlg.comboBoxProfileType.blockSignals(True)
        dlg.comboBoxBase.blockSignals(True)

        # Logic for handling different surface types
        if surface == 'Buildings':
            dlg.textBrowserProfileType.setEnabled(False)
            dlg.textBrowserProfileType.setPlainText('Profile Type (To be developed)')
            dlg.comboBoxProfileType.setEnabled(False)
            dlg.comboBoxProfileType.clear()
            
        elif surface in ['Grass', 'Evergreen Tree', 'Deciduous Tree']:
            dlg.textBrowserProfileType.setEnabled(True)
            dlg.textBrowserProfileType.setPlainText('LAI equation')
            dlg.comboBoxProfileType.clear()
            dlg.comboBoxProfileType.setEnabled(True)
            dlg.comboBoxProfileType.addItems(['0', '1'])
            dlg.comboBoxProfileType.setCurrentIndex(1)

        else:
            dlg.textBrowserProfileType.setEnabled(False)
            dlg.textBrowserProfileType.setPlainText('')
            dlg.comboBoxProfileType.setEnabled(False)
            dlg.comboBoxProfileType.clear()

        # Populate base combo box
        table = db_dict[surf_df_dict[surface]]
        dlg.comboBoxBase.addItems(sorted(table['nameOrigin'][table['Surface'] == surface]))
        dlg.comboBoxBase.setCurrentIndex(-1)

        # List of columns to not show in GUI
        col_list = list(table)
        remove_cols = ['ID', 'Surface', 'Period', 'Origin', 'Name', 'Ref', 'typeOrigin', 'nameOrigin', 'Color']

        if surface != 'Deciduous Tree':
            remove_cols.append('Porosity')  # Exception for just Deciduous tree in Veg

        if surface != 'Water':
            remove_cols.append('Water State')

        if surface != 'Buildings':
            remove_cols.append('Spartacus Surface')

        for col in remove_cols:
            if col in col_list:
                col_list.remove(col)

        for i in range(21):
            getattr(dlg, f'comboBox_{i}').blockSignals(True)
        # Set names of columns and activate comboboxes             
        for i, col_name in enumerate(col_list):
            if i >= 20:
                break
            Oc = getattr(dlg, f'textBrowser_{i}', None)
            if Oc:
                Oc.clear()
                Oc.setEnabled(True)
            Nc = getattr(dlg, f'comboBox_{i}', None)
            if Nc:
                Nc.clear()
                Nc.setEnabled(True)

            Oc.setText(col_name)

            # Logic for populating combo boxes based on column names
            if col_name == 'Spartacus Surface':
                table_sel = db_dict[col_name]
                table_surf = table_sel.drop(columns=['nameOrigin'])
                table_sel = table_sel.reset_index().drop(columns=['ID'])

            elif col_name in ['Leaf Area Index', 'Leaf Growth Power']:
                table_sel = db_dict[col_name]
                LAI_sel = dlg.comboBoxProfileType.currentText()
                try:
                    table_surf = table_sel[(table_sel['Surface'] == surface) & (table_sel['LAIEq'] == int(LAI_sel))]
                except:
                    table_surf = DataFrame()
                    table_surf.iloc[0,'Name'] = 'no avalible'
                    table_surf.iloc[0,'Origin'] = ''
                    
            elif col_name == 'Biogen CO2':
                table_sel = db_dict[col_name]
                table_surf = table_sel[(table_sel['Surface'] == surface) | (table_sel['Surface'] == 'All vegetation')]

            elif col_name.startswith('OHM'):
                table = db_dict['OHM']
                if surface in ['Grass', 'Evergreen Tree', 'Deciduous Tree']:
                    table_surf = table[(table['Surface'] == surface) | (table['Surface'] == 'All vegetation') | (table['Surface'] == 'cropland')]
                elif surface in ['Buildings', 'Paved', 'Bare Soil']:
                    table_surf = table[(table['Surface'] == surface) | (table['Surface'] == 'All nonveg')]
                elif surface == 'Water':
                    table_surf = table[table['Surface'] == surface]
            else:
                table = db_dict[col_name]
                table_surf = table[table['Surface'] == surface]
            
            for i in range(21):
                getattr(dlg, f'comboBox_{i}').blockSignals(False)

            Nc_fill_list = [f"{idx}: {name}, {orig}" for idx, (name, orig) in enumerate(zip(table_surf['Name'], table_surf['Origin']))]
            Nc.addItems(Nc_fill_list)
            Nc.setEnabled(True)
        
        # Deactivate LAIEq Changed function
        dlg.comboBoxProfileType.blockSignals(True)
        dlg.comboBoxBase.blockSignals(False)
        
    def base_typology_changed():
        # Check if a base typology is selected
        if dlg.comboBoxBase.currentIndex() != -1:

            surface = dlg.comboBoxSurface.currentText()
            base_typology = dlg.comboBoxBase.currentText()

            # Retrieve the relevant surface table and row
            surface_table = db_dict[surf_df_dict[surface]]
            surf_row = surface_table[(surface_table['nameOrigin'] == base_typology) & (surface_table['Surface'] == surface)].squeeze().to_dict()

            # Update text fields with selected row data
            dlg.textEditName.setText(surf_row['Name'])
            dlg.textEditOrig.setText(surf_row['Origin'])

            # Iterate through combo boxes and text browsers
            for i in range(21):
                Cb = getattr(dlg, f'comboBox_{i}', None)
                Tb = getattr(dlg, f'textBrowser_{i}', None)

                if Tb and len(Tb.toPlainText()) < 1:
                    break

                if Tb and Cb:
                    
                    cbox_table_indexer = Tb.toPlainText()
                    surf_row_id = surf_row.get(cbox_table_indexer)

                    # Determine if OHM or not
                    cbox_table = db_dict['OHM'] if cbox_table_indexer.startswith('OHM') else db_dict.get(cbox_table_indexer)

                    # Find the correct index for the combo box

                    if cbox_table_indexer in ['Leaf Area Index', 'Leaf Growth Power']:

                        LAI_index = cbox_table.loc[surf_row_id, 'LAIEq'].item()
                        dlg.comboBoxProfileType.setCurrentIndex(dlg.comboBoxProfileType.findText(str(int(LAI_index))))

                        cbox_items = get_combobox_items(Cb)
                        nameOrigin = cbox_table.loc[surf_row_id, 'nameOrigin']
                        cbox_index = cbox_items.index(nameOrigin)

                    else:
                        cbox_items = get_combobox_items(Cb)
                        nameOrigin = cbox_table.loc[surf_row_id, 'nameOrigin']
                        cbox_index = cbox_items.index(nameOrigin)


                    # Set the combo box to the correct index
                        Cb.setCurrentIndex(cbox_index)

    def LAIEq_changed():

        # Check if the surface is one of the specified types
        surface = dlg.comboBoxSurface.currentText()

        if surface in ['Grass', 'Deciduous Tree', 'Evergreen Tree']:
            
            try:
                # Clear and filter Leaf Area Index combo box based on LAIEq
                current_LAIEq = int(dlg.comboBoxProfileType.currentText())
                
                for type_to_check in ['Leaf Area Index', 'Leaf Growth Power']:
                    for j in range(21):
                        Tb = getattr(dlg, f'textBrowser_{j}', None)
                        if Tb and Tb.toPlainText() == type_to_check:
                            Cb = getattr(dlg, f'comboBox_{j}', None)
                            Cb.clear()  # Clear previous items

                            # Get filtered LAI values based on current LAIEq
                            filtered_LAI = db_dict[type_to_check][
                                (db_dict[type_to_check]['LAIEq'] == current_LAIEq) & 
                                (db_dict[type_to_check]['Surface'] == surface)
                            ]
                            LAIList = list(filtered_LAI['nameOrigin'])
                            formatted_list = [f"{k + 1}: {value}" for k, value in enumerate(LAIList)]
                            Cb.addItems(formatted_list)  # Add filtered items

                            getattr(dlg, f'comboBox_{j}').currentIndexChanged.connect(lambda _, idx=j: print_table(idx))

                            break  # Exit after processing the current type
            except:
                pass

    def print_table(idx):
        # Check if a base typology is selected

        if dlg.comboBoxSurface.currentIndex() != -1:
            
            try:
                surface = dlg.comboBoxSurface.currentText()
                # Get the name of the text browser
                Tb_name = getattr(dlg, f'textBrowser_{idx}', None)
                table_var = Tb_name.toPlainText()
                dlg.textBrowserTableLable.setText(table_var)

                # Determine if to use OHM or not
                table = db_dict['OHM'] if table_var.startswith('OHM') else db_dict.get(table_var)

                # Filter the table based on the selected surface
                if surface in ['Grass', 'Evergreen Tree', 'Deciduous Tree']:
                    table_surf = table[(table['Surface'] == surface) | (table['Surface'] == 'All vegetation') | (table['Surface'] == 'cropland')]
                elif surface in ['Buildings', 'Paved', 'Bare Soil']:
                    table_surf = table[(table['Surface'] == surface) | (table['Surface'] == 'All nonveg')]
                elif surface == 'Water':
                    table_surf = table[table['Surface'] == surface]

                # Prepare to display the table, remove columns that not is to show
                col_list = list(table)
                remove_cols = ['ID', 'Surface', 'Period', 'Ref', 'typeOrigin', 'nameOrigin']
                col_list = [col for col in col_list if col not in remove_cols]

                if table_var == 'Spartacus Surface':
                    Tb = getattr(dlg, 'textBrowserEl', None)
                    Tb.clear()

                    table_spar = table.copy()
                    ref_show = db_dict['References']['authorYear'].to_dict()
                    table_spar['Reference'] = table_spar['Ref'].map(ref_show).fillna('')  # Map references
                    mat_show = db_dict['Spartacus Material']['Name'].to_dict()

                    col_order = list(table.columns)

                    for i in range(1, 6):
                        # Use the correct column names with spaces
                        table_spar[f'r{i}Material2'] = table_spar[f'r{i}Material'].map(mat_show)  # Map materials
                        table_spar[f'w{i}Material2'] = table_spar[f'w{i}Material'].map(mat_show)  # Map materials
                        table_spar[f'r{i}Material'] = table_spar[f'r{i}Material2']
                        table_spar[f'w{i}Material'] = table_spar[f'w{i}Material2']

                    table_spar = table_spar.loc[:,col_order]

                    Tb.setText(str(table_spar.reset_index().drop(columns=['ID', 'Ref', 'nameOrigin', 'Surface']).to_html(index=True)))
                    Tb.setLineWrapMode(0)

                elif table_var in ['Leaf Area Index', 'Leaf Growth Power']:

                    LAIEq = dlg.comboBoxProfileType.currentText()
                    LAI = db_dict[table_var][
                        (db_dict[table_var]['Surface'] == surface) & 
                        (db_dict[table_var]['LAIEq'] == int(LAIEq))
                    ]

                    table = LAI.drop(columns=['Surface', 'nameOrigin']).reset_index()
                    
                    Tb = getattr(dlg, 'textBrowserEl', None)
                    Tb.clear()
                    ref_show = db_dict['References']['authorYear'].to_dict()
                    table['Reference'] = table['Ref'].map(ref_show).fillna('')  # Map references
                    Tb.setText(str(table.drop(columns=['Ref', 'ID']).to_html(index=True)))
                    Tb.setLineWrapMode(0)
                
                else:
                    Tb = getattr(dlg, 'textBrowserEl', None)
                    Tb.clear()
                    ref_show = db_dict['References']['authorYear'].to_dict()
                    table_surf['Reference'] = table_surf['Ref'].map(ref_show).fillna('')  # Map references
                    Tb.setText(str(table_surf.reset_index().drop(columns=['Ref', 'ID', 'Surface']).to_html(index=True)))
                    Tb.setLineWrapMode(0)

            except:
                pass #TODO Fix better solution to avoid error when changing surfaces
    
    def check_typology(): # 
        # TODO Add more checkerse

        otf_nameOrigin = str(dlg.textEditName.value()) + ', ' + str(dlg.textEditOrig.value()) 
    
        # Ensure that user does not create same name as already exist
        if len(dlg.comboBoxSurface.currentText()) <1: 
            QMessageBox.warning(None, 'Surface Missing','Please select a surface')
            pass
        elif dlg.textEditName.value().startswith('test'):
            QMessageBox.warning(None, 'Error in Name','Please, don´t use test as type name..')
        elif dlg.textEditName.value().startswith('Test'):
            QMessageBox.warning(None, 'Error in Name','Please, don´t use test as type name..')
        elif len(dlg.textEditName.text()) <1: 
            QMessageBox.warning(None, 'Name Missing','Please fill in the Name Box')
            pass
        elif len(dlg.textEditOrig.text()) <1: 
            QMessageBox.warning(None, 'Origin Missing','Please fill in the Origin Box')
            pass
        elif otf_nameOrigin == dlg.comboBoxBase.currentText():
            QMessageBox.warning(None, 'Nameing Error','Name and origin Matches what already is in DB')
            pass
        else:
            generate_typology()
        
        
    def generate_typology():

        # Nonveg or veg or water?
        surface = dlg.comboBoxSurface.currentText()

        table = db_dict[surf_df_dict[surface]]
        col_list = list(table)
        remove_cols = ['ID', 'Name', 'Surface', 'Period', 'Origin', 'Type', 'nameOrigin']
        
        if surface != 'Water':
            remove_cols.append('Water State')
        if surface == 'Grass' or surface == 'Evergreen Tree':
            remove_cols.append('Porosity')

        col_list = [i for i in col_list if i not in remove_cols]

        dict_reclass = {
            'ID' : create_code(surf_df_dict[surface]),
            'Surface' : surface,
            'Origin' : str(dlg.textEditOrig.value()),
            'Name' : str(dlg.textEditName.value()),
        }
        
        for i in range(21):
            Nc = getattr(dlg, f'comboBox_{i}', None)
            Oc = getattr(dlg, f'textBrowser_{i}', None)

            if len(Oc.toPlainText()) <1:
                break
            else:
                oldField = Oc.toPlainText()
                sel_att = Nc.currentText()

                if oldField.startswith('OHM'):  
                    table = db_dict['OHM']
                else:               
                    table = db_dict[oldField]
            
                sel_att = sel_att.split(': ')[1] # Remove number added for interpretation in GUI

                newField = table[table['nameOrigin'] == sel_att].index.item()
                dict_reclass[oldField] = newField       
                table.drop(columns = 'nameOrigin')
            
        new_edit = DataFrame([dict_reclass]).set_index('ID')
        
        db_dict[surf_df_dict[surface]] = concat([db_dict[surf_df_dict[surface]], new_edit])
    
        save_to_db(db_path, db_dict)
   
        QMessageBox.information(None, 'Sucessful','Typology entry added to local database')
        
        fill_cbox() # reset tab

    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 2:
            fill_cbox()

    dlg.comboBoxSurface.currentIndexChanged.connect(changed_surface)
    dlg.comboBoxBase.currentIndexChanged.connect(base_typology_changed)
    dlg.comboBoxProfileType.currentIndexChanged.connect(LAIEq_changed)
    dlg.pushButtonGen.clicked.connect(check_typology)

    self.dlg.tabWidget.currentChanged.connect(tab_update)

    dlg.comboBox_0.currentIndexChanged.connect(lambda: print_table(0))
    dlg.comboBox_1.currentIndexChanged.connect(lambda: print_table(1))
    dlg.comboBox_1.currentIndexChanged.connect(lambda: print_table(1))
    dlg.comboBox_2.currentIndexChanged.connect(lambda: print_table(2))
    dlg.comboBox_3.currentIndexChanged.connect(lambda: print_table(3))
    dlg.comboBox_4.currentIndexChanged.connect(lambda: print_table(4))
    dlg.comboBox_5.currentIndexChanged.connect(lambda: print_table(5))
    dlg.comboBox_6.currentIndexChanged.connect(lambda: print_table(6))
    dlg.comboBox_7.currentIndexChanged.connect(lambda: print_table(7))
    dlg.comboBox_8.currentIndexChanged.connect(lambda: print_table(8))
    dlg.comboBox_9.currentIndexChanged.connect(lambda: print_table(9))
    dlg.comboBox_10.currentIndexChanged.connect(lambda: print_table(10))
    dlg.comboBox_11.currentIndexChanged.connect(lambda: print_table(11))
    dlg.comboBox_12.currentIndexChanged.connect(lambda: print_table(12))
    dlg.comboBox_13.currentIndexChanged.connect(lambda: print_table(13))
    dlg.comboBox_14.currentIndexChanged.connect(lambda: print_table(14))
    dlg.comboBox_15.currentIndexChanged.connect(lambda: print_table(15))
    dlg.comboBox_16.currentIndexChanged.connect(lambda: print_table(16))
    dlg.comboBox_17.currentIndexChanged.connect(lambda: print_table(17))
    dlg.comboBox_18.currentIndexChanged.connect(lambda: print_table(18))
    dlg.comboBox_19.currentIndexChanged.connect(lambda: print_table(19))
    dlg.comboBox_20.currentIndexChanged.connect(lambda: print_table(20))
