from pandas import DataFrame, concat
from qgis.PyQt.QtWidgets import QMessageBox
from .database_functions import param_info_dict, create_code, save_to_db, ref_changed, get_limits_from_json_schema
# import pandas as pd
import re 

#################################################################################################
#                                                                                               #
#                                        Parameter Creator                                      #
#                                                                                               #
#################################################################################################

def setup_parameter_creator(self, dlg, db_dict, db_path):

    def fill_cbox():
        dlg.comboBoxSurface.blockSignals(True)
        dlg.comboBoxTableSelect.blockSignals(True)
        
        dlg.comboBoxRef.clear()
        dlg.comboBoxRef.addItems(sorted(db_dict['References']['authorYear'])) 
        dlg.comboBoxRef.setCurrentIndex(-1)
        dlg.comboBoxBase.clear()

        dlg.comboBoxSurface.setCurrentIndex(-1)

        dlg.comboBoxTableSelect.clear()
        dlg.comboBoxTableSelect.addItems(sorted(param_info_dict.keys()))
        dlg.comboBoxTableSelect.setCurrentIndex(-1)

        dlg.textEditName.clear()
        dlg.textEditOrig.clear()


        for i in range(0,15):
            Oc = getattr(dlg, f'textBrowser_{i}')
            Oc.clear()
            Oc.setDisabled(True)
            Nc = getattr(dlg, f'textEdit_Edit_{i}')
            Nc.clear()
            Nc.setDisabled(True)
        
        dlg.comboBoxSurface.blockSignals(False)
        dlg.comboBoxTableSelect.blockSignals(False)

    def table_changed():

        if dlg.comboBoxTableSelect.currentIndex() != -1:
            dlg.comboBoxBase.clear()
            dlg.comboBoxSeason.setDisabled(True)
            dlg.comboBoxSeason.setCurrentIndex(-1)
            dlg.textBrowserSeason.setDisabled(True)
        
            table_name = dlg.comboBoxTableSelect.currentText()
            dlg.textBrowserDf.clear()
            
            for i in range(0,15):
                Oc = getattr(dlg, f'textBrowser_{i}')
                Oc.clear()
                Oc.setDisabled(True)
                Nc = getattr(dlg, f'textEdit_Edit_{i}')
                Nc.clear()
                Nc.setDisabled(True)

                # Set surfaces that uses the selcted table
                dlg.comboBoxSurface.clear()

                dlg.comboBoxSurface.addItems(param_info_dict[table_name]['surface'])
                dlg.comboBoxSurface.setEnabled(True)

                # Add correct parameters for selected table
                params = list(param_info_dict[table_name]['param'].keys())
            
                for idx in range(len(params)):
                    Oc = getattr(dlg, f'textBrowser_' + str(idx))
                    Oc.setEnabled(True)
                    Oc.setText(str(params[idx]))
                    Oc.setToolTip(param_info_dict[table_name]['param'][params[idx]]['tooltip'])
                    Nc = getattr(dlg, f'textEdit_Edit_' + str(idx))
                    Nc.setEnabled(True)

            if table_name == 'OHM':
                dlg.comboBoxSeason.setEnabled(True)
                dlg.comboBoxSeason.setCurrentIndex(0)
                dlg.textBrowserSeason.setEnabled(True)

            elif table_name in ['Conductance', 'Soil']:
                dlg.comboBoxSurface.setEnabled(False)
            
            # dlg.comboBoxSurface.setCurrentIndex(-1)

    def surface_changed():

        if dlg.comboBoxTableSelect.currentIndex() != -1:

            surface_sel = dlg.comboBoxSurface.currentText()
            table_name = dlg.comboBoxTableSelect.currentText()

            if table_name in ['Soil', 'Conductance']:  
                current_parameters = db_dict[table_name]
            else:
                current_parameters = db_dict[table_name][db_dict[table_name]['Surface'] == surface_sel]

            dlg.comboBoxBase.clear()
            dlg.comboBoxBase.addItems(current_parameters['nameOrigin'].tolist())
            dlg.comboBoxBase.setEnabled(True)
            dlg.comboBoxBase.setCurrentIndex(-1)
            dlg.textEditName.clear()
            dlg.textEditOrig.clear()

            params = list(param_info_dict[table_name]['param'].keys())
            
            for idx in range(len(params)):
                Nc = getattr(dlg, f'textEdit_Edit_' + str(idx))
                Nc.clear()
        
        if dlg.comboBoxSurface.currentIndex() != -1:
            print_table()   


    def base_parameter_changed():
        surface_sel = dlg.comboBoxSurface.currentText()
        dlg.comboBoxRef.setCurrentIndex(-1)
        base_str = dlg.comboBoxBase.currentText()
        if base_str != '': 
            table_name = dlg.comboBoxTableSelect.currentText()

            if table_name in ('Conductance','Soil'):
                base_parameter = db_dict[table_name].loc[db_dict[table_name]['nameOrigin'] == base_str]                       
            else:
                base_parameter = db_dict[table_name][db_dict[table_name]['Surface'] == surface_sel].loc[db_dict[table_name]['nameOrigin'] == base_str]                        
    
            params = list(param_info_dict[table_name]['param'].keys())

            try:
                for idx in range(len(params)):
                    Oc = getattr(dlg, f'textBrowser_' + str(idx))
                    Nc = getattr(dlg, f'textEdit_Edit_' + str(idx))
                    param_sel = base_parameter[Oc.toPlainText()]
                    Nc.setValue(str(round(param_sel.item(),3)))
            except:
                pass
            
            ref_id = base_parameter['Ref']
            ref_index = db_dict['References'].loc[ref_id, 'authorYear'].item()
            dlg.comboBoxRef.setCurrentIndex(dlg.comboBoxRef.findText(ref_index))


    def print_table():
        # Check if a base typology is selected

        surface = dlg.comboBoxSurface.currentText()
        # Get the name of the text browser
        Tb = dlg.textBrowserDf
        table_var = dlg.comboBoxTableSelect.currentText()

        if table_var == 'Conductance':
            table_show = db_dict['Conductance']  

            Tb.clear()
            ref_show = db_dict['References']['authorYear'].to_dict()
            table_show['Reference'] = table_show['Ref'].map(ref_show).fillna('')  # Map references
            Tb.setText(str(table_show.reset_index().drop(columns=['Ref', 'ID']).to_html(index=True)))
            Tb.setLineWrapMode(0)

        else:
            # Determine if to use OHM or not
            table = db_dict['OHM'] if table_var.startswith('OHM') else db_dict.get(table_var)

            # Filter the table based on the selected surface
            if surface in ['Grass', 'Evergreen Tree', 'Deciduous Tree']:
                table_surf = table[(table['Surface'] == surface) | (table['Surface'] == 'All vegetation') | (table['Surface'] == 'cropland')]
            elif surface in ['Buildings', 'Paved', 'Bare Soil']:
                table_surf = table[(table['Surface'] == surface) | (table['Surface'] == 'All nonveg')]
            else:
                table_surf = table[table['Surface'] == surface]

            Tb.clear()
            ref_show = db_dict['References']['authorYear'].to_dict()
            table_surf['Reference'] = table_surf['Ref'].map(ref_show).fillna('')  # Map references
            Tb.setText(str(table_surf.reset_index().drop(columns=['Ref', 'ID', 'Surface']).to_html(index=True)))
            Tb.setLineWrapMode(0)


    def add_table():

        table_name = dlg.comboBoxTableSelect.currentText()
        table = db_dict[table_name]
        if table_name == 'Conductance':
            columns_to_remove = ['Name','Origin','Ref', 'nameOrigin','Reference'] #'General Type',
        elif table_name == 'OHM':
            columns_to_remove = ['Surface', 'Name','Origin','Ref', 'nameOrigin', 'Season'] #'General Type', 
        else:
            columns_to_remove = ['Surface', 'Name','Origin','Ref', 'nameOrigin'] #'General Type', 
        table_list = list(table)

        for remove in columns_to_remove:
                table_list.remove(remove)

        len_list = len(table_list)

        if table_name == 'Soil':
            dict_reclass = {
                'ID' : create_code(table_name),
                'Surface' : 'NaN', 
                'Name' : dlg.textEditName.value(),
                'Origin' : dlg.textEditOrig.value()
            }

        elif table_name == 'conductance':
            dict_reclass = {
                'ID' : create_code(table_name),
                'Name' : dlg.textEditName.value(),
                'Origin' : dlg.textEditOrig.value()
            }
        
        else:
            dict_reclass = {
                'ID' : create_code(table_name),
                'Surface' : dlg.comboBoxSurface.currentText(), 
                'Name' : dlg.textEditName.value(),
                'Origin' : dlg.textEditOrig.value() 
            }
            
            if dlg.comboBoxTableSelect.currentText() == 'OHM':
                dict_reclass['Season'] = dlg.comboBoxSeason.currentText()
    
        for idx in range(len_list):
            # Left side
            Oc = getattr(dlg, f'textBrowser_' + str(idx))
            if len(Oc.toPlainText()) <1:
                break
            oldField = Oc.toPlainText()
            # Right Side
            Nc = getattr(dlg, f'textEdit_Edit_' + str(idx))
            try:
                newField = float(Nc.value())
            except:
                QMessageBox.warning(None, oldField + ' Error','Invalid characters in ' + oldField + '\nOnly 0-9 and . are allowed')
                return
            
            dict_reclass[oldField] =  newField

        if not dlg.comboBoxRef.currentText():
            QMessageBox.warning(None, 'Reference Info Missing','Please add information')
            return
        else:
            dict_reclass['Ref'] = db_dict['References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item() 
        
        new_edit = DataFrame([dict_reclass]).set_index('ID')
        db_dict[table_name] = concat([db_dict[table_name], new_edit])        

        checker = checkerInput(table_list)

        if not checker == 1:
            db_dict[table_name] = db_dict[table_name].drop(new_edit.index, errors='ignore')
        else:
            QMessageBox.information(None, 'Succesful', table_name + ' Entry added to your local database')

            save_to_db(db_path, db_dict)
            tab_update()
            # table_changed() #TODO Fix so that table, when updated is shown directly

    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 3:
            fill_cbox()

    def checkerInput(table_list):

        checker = 1
        
        def special_match(strg, search=re.compile(r'[^0-9.-]').search):
            return not bool(search(strg))

        var = dlg.comboBoxTableSelect.currentText()
        
        if len(dlg.comboBoxSurface.currentText()) <1: 
            if var != 'Soil':
                QMessageBox.warning(None, 'Surface Missing','Please select a surface')
                return
        elif len(dlg.textEditName.value()) <1: 
            QMessageBox.warning(None, 'Name Missing','Please fill in the Name Box')
            return
        elif len(dlg.textEditOrig.value()) <1: 
            QMessageBox.warning(None, 'Origin Missing','Please fill in the Origin Box')
            return
        elif len(dlg.comboBoxRef.currentText()) <1:
            QMessageBox.warning(None, 'References Missing','Please select a references')
            return

        # Check if valid numbers are added
        len_list = len(table_list)
        for idx in range(len_list):
            # Left side
            Oc = getattr(dlg, f'textBrowser_' + str(idx))
            oldField = Oc.toPlainText()
            vars()[dlg, f'textBrowser_' + str(idx)] = Oc
            # Right Side
            Nc = getattr(dlg, f'textEdit_Edit_' + str(idx))
            if(len(Nc.value())) <1:
                QMessageBox.warning(None, oldField + ' Missing','Enter value for ' + oldField)
                return

            if Oc.toPlainText() != 'Season': # Add more to where this is fine!
                if  special_match(Nc.value()) == False:
                    QMessageBox.warning(None, oldField + ' Error','Invalid characters in ' + oldField + '\nOnly 0-9 and . are allowed')
                    return
                
        #   # Example: Get limits for pormin_dec from json schema
        # limits = get_limits_from_json_schema("laimin")

        # if limits:
        #     print(f"Variable: {limits['variable']}")
        #     print(f"Valid range: {limits['min']} to {limits['max']}")
        #     print(f"Default: {limits['default']}")
        #     print(f"Unit: {limits['unit']}")
        #     print(f"Description: {limits['description']}")
        # else:
        #     print("Variable not found in schema")

        if var == 'Albedo':
            limMin = get_limits_from_json_schema("alb_min")
            limMax = get_limits_from_json_schema("alb_max")
            if float(dlg.textEdit_Edit_0.value()) < limMin['min'] or float(dlg.textEdit_Edit_0.value()) > limMin['max']:
                QMessageBox.warning(None, 'Albedo Min error','Alb_min must be between 0-1')
                return
            elif float(dlg.textEdit_Edit_1.value()) < limMax['min'] or float(dlg.textEdit_Edit_1.value()) > limMax['max']:
                QMessageBox.warning(None, 'Albedo Max error','Alb_max must be between 0-1')
                return
            elif float(dlg.textEdit_Edit_0.value()) > float(dlg.textEdit_Edit_1.value()):
                QMessageBox.warning(None, 'Value error', dlg.textBrowser_0.toPlainText() + ' must be smaller or equal to ' + dlg.textBrowser_1.toPlainText())
                return

        elif var == 'Leaf Area Index':
            if float(dlg.textEdit_Edit_1.value()) < 0 or float(dlg.textEdit_Edit_1.value()) > 1:
                QMessageBox.warning(None, 'LAImin error','LAImin must be between 0-1')
                return
            elif float(dlg.textEdit_Edit_2.value()) < 0 or float(dlg.textEdit_Edit_2.value()) > 1:
                QMessageBox.warning(None, 'LAImax error','LAImax must be between 0-1')
                return
            elif float(dlg.textEdit_Edit_1.value()) > float(dlg.textEdit_Edit_2.value()):
                QMessageBox.warning(None, 'Value error', dlg.textBrowser_1.toPlainText() + ' must be smaller or equal to ' + dlg.textBrowser_2.toPlainText())
                return
            elif int(dlg.textEdit_Edit_0.value()) > 1:
                QMessageBox.warning(None, 'LAI Equation error','LAIeq choices are 0 or 1')
                return

        elif var == 'Porosity':
            if float(dlg.textEdit_Edit_0.value()) > float(dlg.textEdit_Edit_1.value()):
                QMessageBox.warning(None, 'Value error', dlg.textBrowser_0.toPlainText() + ' must be smaller or equal to ' + dlg.textBrowser_1.toPlainText())
                return

        elif var == 'Emissivity':
            if float(dlg.textEdit_Edit_0.value()) < 0 or float(dlg.textEdit_Edit_0.value()) > 1:
                QMessageBox.warning(None, 'Emissivity error','Emissivity must be between 0-1')
                return
        elif var == 'Conductance':
            if float(dlg.textEdit_Edit_11.value()) <1 or float(dlg.textEdit_Edit_11.value()) >2:
                QMessageBox.warning(None, 'gsModel error','gsModel Choices are 1 & 2')
                return
            
        return checker


    def to_ref_edit():
        self.dlg.tabWidget.setCurrentIndex(10)

    dlg.pushButtonToRefManager.clicked.connect(to_ref_edit)
    dlg.comboBoxTableSelect.currentIndexChanged.connect(table_changed) 
    dlg.pushButtonGen.clicked.connect(add_table)
    dlg.comboBoxRef.currentIndexChanged.connect(lambda: ref_changed(dlg, db_dict))    
    dlg.comboBoxBase.currentIndexChanged.connect(base_parameter_changed)
    dlg.comboBoxSurface.currentIndexChanged.connect(surface_changed)
    self.dlg.tabWidget.currentChanged.connect(tab_update)
