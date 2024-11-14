from pandas import DataFrame, concat
from qgis.PyQt.QtWidgets import QMessageBox
from PyQt5.QtWidgets import  QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from .database_functions import save_to_db, create_code, ref_changed

from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp


#################################################################################################
#                                                                                               #
#                                  Profile creator (Profiles)                                   #
#                                                                                               #
#################################################################################################

def setup_profile_creator(self, dlg, db_dict, db_path):

    def fill_cbox():

        db_dict['Profiles']['baseProfIndexer'] = [f"{row['Name']}, {row['City']}" for index, row in db_dict['Profiles'].iterrows()]

        dlg.comboBoxMain.clear()
        dlg.comboBoxSub.clear()

        dlg.comboBoxRef.addItems(sorted(db_dict['References']['authorYear']))
        dlg.comboBoxRef.setCurrentIndex(-1)

        if dlg.radioButtonProfile.isChecked() is True:
            profile_setting('Profile')

        # set up rules for profile LineEdits
        # Only 5
        # only 0-9 and .
        reg_ex = QRegExp("[0-9.]*")  
              
        for i in range(24):
            Le = getattr(dlg, f'lineEdit_{i}')
            Le.setMaxLength(5)
            input_validator = QRegExpValidator(reg_ex, Le)
            Le.setValidator(input_validator)


    def profile_setting(setting):

        dlg.comboBoxSub.blockSignals(True)
        dlg.comboBoxMain.clear()

        if setting == 'Profile':
            
            dlg.textBrowserMain.setText('Profile Type')
            dlg.comboBoxMain.addItems(['Human activity', 'Population density', 'Energy use', 'Traffic', 'Water use (manual)','Water use (automatic)','Snow removal'])
            dlg.comboBoxMain.setCurrentIndex(-1)
            
            dlg.textBrowserSub.setText('Country')
            dlg.comboBoxSub.clear()
            dlg.comboBoxDay.clear()
            dlg.comboBoxBaseProfile.clear()

        elif setting == 'Country':
            dlg.textBrowserMain.setText('Country')

            dlg.comboBoxMain.addItems(sorted(list(set(db_dict['Profiles']['Country']))))
            dlg.comboBoxMain.setCurrentIndex(-1)

            dlg.textBrowserSub.setText('Profile Type')
            dlg.comboBoxSub.clear()
            dlg.comboBoxDay.clear()
            dlg.comboBoxBaseProfile.clear()

        dlg.comboBoxSub.blockSignals(False)

    def main_changed():

        dlg.comboBoxSub.blockSignals(True)

        if dlg.radioButtonProfile.isChecked() is True:

            # 1. Check for country
            if dlg.comboBoxMain.currentText() == '':
                pass 
            else:
                dlg.comboBoxSub.clear()
                dlg.comboBoxDay.clear()
                dlg.comboBoxBaseProfile.clear()
                main_sel_sel = dlg.comboBoxMain.currentText()
                country_list = sorted(list(set(list(db_dict['Profiles']['Country'].loc[db_dict['Profiles']['Profile Type'] == main_sel_sel]))))
                dlg.comboBoxSub.addItems(sorted(country_list))
                dlg.comboBoxSub.setCurrentIndex(-1)
                dlg.comboBoxRef.setCurrentIndex(-1)
        else:

            # 1. Check for country
            if dlg.comboBoxMain.currentText() == '':
                pass 
            else:
                dlg.comboBoxSub.clear()
                dlg.comboBoxDay.clear()
                dlg.comboBoxBaseProfile.clear()
                main_sel = dlg.comboBoxMain.currentText()
                profile_list = list(set(list(db_dict['Profiles']['Profile Type'].loc[db_dict['Profiles']['Country'] == main_sel])))
                dlg.comboBoxSub.addItems(sorted(profile_list))
                dlg.comboBoxSub.setCurrentIndex(-1)
                dlg.comboBoxRef.setCurrentIndex(-1)
    
        dlg.comboBoxSub.blockSignals(False)
        
    def sub_changed():

        dlg.comboBoxDay.blockSignals(True)

        if dlg.comboBoxMain.currentText() == '' and dlg.comboBoxSub.currentText() == '':
            pass

        else:
            dlg.comboBoxRef.setCurrentIndex(-1)

            if dlg.radioButtonProfile.isChecked() is True:
                main_sel = dlg.comboBoxMain.currentText()
                sub_sel = dlg.comboBoxSub.currentText()

                profiles = db_dict['Profiles'][(db_dict['Profiles']['Profile Type'] == main_sel) & (db_dict['Profiles']['Country'] == sub_sel) ]
                day_list = list(set(list(profiles['Day'])))

                current_days = []
                for i in range(dlg.comboBoxDay.count()):
                    current_days.append(dlg.comboBoxDay.itemText(i))

                if current_days == day_list:
                    day_changed()
                else:
                    dlg.comboBoxDay.clear()
                    dlg.comboBoxDay.addItems(day_list)
                    dlg.comboBoxDay.setCurrentIndex(1)
                    day_changed()
            else:

                main_sel = dlg.comboBoxMain.currentText()
                sub_sel = dlg.comboBoxSub.currentText()
                dlg.comboBoxRef.setCurrentIndex(-1)

                profiles = db_dict['Profiles'][(db_dict['Profiles']['Profile Type'] == sub_sel) & (db_dict['Profiles']['Country'] == main_sel)]
                day_list = list(set(list(profiles['Day'])))
                
                current_days = []
                for i in range(dlg.comboBoxDay.count()):
                    current_days.append(dlg.comboBoxDay.itemText(i))

                if current_days == day_list:
                    day_changed()
                else:
                    dlg.comboBoxDay.clear()
                    dlg.comboBoxDay.addItems(day_list)
                    day_changed()
        
        dlg.comboBoxDay.blockSignals(False)
        

    def day_changed():
        main_sel = dlg.comboBoxMain.currentText()
        sub_sel = dlg.comboBoxSub.currentText()
        day_sel = dlg.comboBoxDay.currentText()
        dlg.comboBoxRef.setCurrentIndex(-1)

            
        if dlg.comboBoxMain.currentText() == '' and dlg.comboBoxSub.currentText() == '' and dlg.comboBoxDay.currentText() =='' :
            pass 
        else:

            if dlg.radioButtonProfile.isChecked() is True:

                dlg.comboBoxBaseProfile.clear()

                profiles = db_dict['Profiles'][(db_dict['Profiles']['Day'] == day_sel) & (db_dict['Profiles']['Profile Type'] == main_sel) & (db_dict['Profiles']['Country'] == sub_sel)]

                dlg.comboBoxBaseProfile.clear()
                dlg.comboBoxBaseProfile.addItems(sorted(profiles['baseProfIndexer']))
        
            else:
                
                dlg.comboBoxBaseProfile.clear()

                profiles = db_dict['Profiles'][(db_dict['Profiles']['Day'] == day_sel) & (db_dict['Profiles']['Profile Type'] == sub_sel) & (db_dict['Profiles']['Country'] == main_sel)]

                dlg.comboBoxBaseProfile.clear()
                dlg.comboBoxBaseProfile.addItems(sorted(profiles['baseProfIndexer']))

    def base_prof_changed():
        main_sel = dlg.comboBoxMain.currentText()
        sub_sel = dlg.comboBoxSub.currentText()
        day_sel = dlg.comboBoxDay.currentText()
        base_sel = dlg.comboBoxBaseProfile.currentText()
            
        if main_sel == '' and sub_sel == '' and day_sel =='' and base_sel == '':
            pass

        else:
            if dlg.radioButtonProfile.isChecked() is True:
                prof_sel = db_dict['Profiles'][
                    (db_dict['Profiles']['Day'] == day_sel) & (db_dict['Profiles']['Profile Type'] == main_sel) & 
                    (db_dict['Profiles']['Country'] == sub_sel)  & (db_dict['Profiles']['baseProfIndexer'] ==base_sel)]
                
            else:
                prof_sel = db_dict['Profiles'][
                    (db_dict['Profiles']['Day'] == day_sel) & (db_dict['Profiles']['Profile Type'] == sub_sel) & 
                    (db_dict['Profiles']['Country'] == main_sel)  & (db_dict['Profiles']['baseProfIndexer'] ==base_sel)]
                
            prof_sel.columns = prof_sel.columns.map(str)
            prof_sel_dict = prof_sel.squeeze().to_dict()

            try:
                ref_id = prof_sel['Ref']
                ref_index = db_dict['References'].loc[ref_id, 'authorYear'].item()
                dlg.comboBoxRef.setCurrentIndex(dlg.comboBoxRef.findText(ref_index))
            except:
                print('error in showing References')
            # try:
            #     # Set reference for profile
            #     ref_sel = prof_sel['Ref'].item()
            #     ref_str = db_dict['References'].loc[ref_sel, 'authorYear']

            #     ref_index = dlg.comboBoxRef.findText(ref_str)
            #     dlg.comboBoxRef.setCurrentIndex(ref_index)
            # except:
            #     pass

        plotValues = []
        for i in range(24):
            Tb = getattr(dlg, f'textBrowser_{i}')
            Le = getattr(dlg, f'lineEdit_{i}')
            Le.clear()
            Le.setText(str(prof_sel_dict[str(Tb.toPlainText())]))
            
            try:
                plotValues.append(float(prof_sel_dict[str(Tb.toPlainText())]))
            except:
                pass

        ## Plot the profile
        
        # Create dataframe from selected profile values
        prof_df = DataFrame(plotValues)
        # Check if df is empty to avoid errors from trying to plot nans
        # TODO Make a plot showing NAN values or make sure that nan is instead -9999 in Database
        if prof_df.empty is True:
            pass
        else:
            # Check if plotViewer.layout() exists, to be sure that no errors are given when cleaning
            if dlg.plotViewer.layout() is None:
                layout = QVBoxLayout(dlg.plotViewer)
                dlg.plotViewer.setLayout(layout)
            else:
                layout = dlg.plotViewer.layout()
            
            # clean dlg.plotViewer
            for i in reversed(range(layout.count())):
                widget_to_remove = layout.itemAt(i).widget()
                layout.removeWidget(widget_to_remove)
                widget_to_remove.setParent(None)
            
            # Create plot from dataframe
            fig, ax = plt.subplots()
            # Adjust figure size
            fig.subplots_adjust(0.1, 0.2, 0.9, 1)
            prof_df.plot(ax=ax, legend=None)
            ax.set_xlim([0, 23])
            ax.set_xticks([0, 6, 12, 18, 23])
            ax.minorticks_on()
            ax.set_xlabel('Hours')
            # Add plot to FigureCanvas object and add to layout Widget
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            
                
    def update_plot():
        a =  dlg.comboBoxMain.currentText() # Not sure why this has to be here, but if i remove it, nothing works...

        plotValues = []
        for i in range(24):
            Le = getattr(dlg, f'lineEdit_{i}')
            val = Le.text()
            plotValues.append(float(val))

        prof_df = DataFrame(plotValues)

        if dlg.plotViewer.layout() is None:
                layout = QVBoxLayout(dlg.plotViewer)
                dlg.plotViewer.setLayout(layout)
        else:
            layout = dlg.plotViewer.layout()
        
        # clean dlg.plotViewer
        for i in reversed(range(layout.count())):
            plt.close()
            widget_to_remove = layout.itemAt(i).widget()
            layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
        
        # Create plot from dataframe
        fig, ax = plt.subplots()
        # Adjust figure size # THIS MIGHT NEED TO CHANGE. Check at more screens than just one..
        fig.subplots_adjust(0.1, 0.2, 0.9, 1)
        prof_df.plot(ax = ax,
                legend=None)
        ax.set_xlim([0,23])
        ax.set_xticks([0,6,12,18,23])
        ax.minorticks_on()
        ax.set_xlabel('Hours')
        # Add plot to FigureCanvas object and add to layout Widget
        canvas = FigureCanvas(fig)
        plt.close()
        layout.addWidget(canvas)

    def add_profile():
    
        if dlg.radioButtonProfile.isChecked() is True:
            profile_type = dlg.comboBoxMain.currentText()
            country = dlg.comboBoxSub.currentText()
        else:
            profile_type = dlg.comboBoxSub.currentText()
            country = dlg.comboBoxMain.currentText()


        dict_reclass = {
            'ID' : create_code('Profiles'),
            'General Type' : 'Reg',
            'Profile Type' : profile_type, 
            'Country' : country,
            'Day' : dlg.comboBoxDay.currentText(),
            'Name' : dlg.textEditName.value(),
            'City' : dlg.textEditCity.value(),
            'Ref' : db_dict['References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item() 
        }

        for i in range(0, 24): 
            Tb = getattr(dlg, f'textBrowser_{i}')
            Le = getattr(dlg, f'lineEdit_{i}')
            col = int(Tb.toPlainText())
            val = Le.text()
            dict_reclass[col] = val

        dict_reclass['Ref'] = db_dict[ 'References'][db_dict['References']['authorYear'] ==  dlg.comboBoxRef.currentText()].index.item() 
        new_edit = DataFrame([dict_reclass]).set_index('ID')
        db_dict['Profiles'] = concat([db_dict['Profiles'], new_edit])

        # Write to db
        save_to_db(db_path, db_dict)

        QMessageBox.information(None, 'Succesful', 'Profile Entry added to your local database')
        fill_cbox()

    def tab_update():
        if self.dlg.tabWidget.currentIndex() == 5:
            fill_cbox()

    def to_ref_edit():
        self.dlg.tabWidget.setCurrentIndex(10)
    

    dlg.pushButtonToRefManager.clicked.connect(to_ref_edit)

    self.dlg.tabWidget.currentChanged.connect(tab_update)
    dlg.radioButtonProfile.toggled.connect(lambda: profile_setting('Profile'))
    dlg.radioButtonCountry.toggled.connect(lambda: profile_setting('Country'))
    dlg.comboBoxRef.currentIndexChanged.connect(lambda: ref_changed(dlg, db_dict))    

    dlg.pushButtonGen.clicked.connect(add_profile)
    dlg.pushButtonUpdatePlot.clicked.connect(update_plot)
    
    dlg.comboBoxMain.currentIndexChanged.connect(main_changed)
    dlg.comboBoxSub.currentIndexChanged.connect(sub_changed)
    dlg.comboBoxBaseProfile.currentIndexChanged.connect(base_prof_changed)
    dlg.comboBoxDay.currentIndexChanged.connect(day_changed)
