## Quick start

[QGIS](http://www.qgis.org) Combo Manager is a python module to easily manage a combo box with
a layer list and eventually relate it with one or several combos with
list of corresponding fields.

The field combos are filled with the names of columns of the currently
selected layer in the layer combo.

In your plugin, create first a _LayerCombo_:

```python
from qgiscombomanager import *

self.layerComboManager = VectorLayerCombo(self.layerComboWidget)
```


Then, associates some _FieldCombo_:

```python
self.myFieldComboManager = FieldCombo(self.myFieldComboManager, self.layerComboManager)
```


The managers (layer or field) must be saved as a class property (self.something), so the variable is not
getting out of scope in python.

The classes offers some convenience methods: `getLayer()` and `setLayer(layer)`, for layer combos, and `getFieldName()`, `getFieldAlias()`, `getFieldIndex()` for field combos.


## Layer Combos

A combo box can be assigned to list the layers. Three classes are available:

```python
LayerCombo(widget, initLayer="", options={}, layerType=None)
VectorLayerCombo(widget, initLayer="", options={})
RasterLayerCombo(widget, initLayer="", options={})
```

`VectorLayerCombo` and `RasterLayerCombo` are convenient classes which are calling the main LayerCombo class with the same parameters and specifying the `layerType`.

* **widget**: the QComboBox widget
* **initLayer**: the initally selected layer ID or a lambda function returning the ID (it could look for a value in settings).
* **options**: a dictionnary of options: {"opt1": val1, "opt2": val2, etc.}.

**Options** are listed hereunder, default values being listed first:
* **hasGeometry***: None/True/False. Restrains the possible selection of layers to layers having or not geometry (None = all).
* **geomType***: None/QGis.Point/QGis.Line/QGis.Polygon. Restrains the possible selection of layers to a certain [type of geometry](http://qgis.org/api/classQGis.html#a09947eb19394302eeeed44d3e81dd74b) (None = all).
* **dataProvider**: None/postgres/etc. Filters the layers based on the data provider name (None = all).
* **groupLayers**: False/True. Groups layers in combobox according to the legend interface groups.
* **legendInterface**: if `groupLayers is True`, you must provide `iface.legendInterface()` for this option.
* **finishInit**: True/False. Set it to  `False` if the `LayerCombo` object must be returned before its items are filled with layers.
* **skipLayers**: a list of layer IDs or lambda functions returning layer IDs which will not to be shown in the combo box.

*used for vector layer combos

This class offer convenient methods:

* `getLayer()`: returns the layer currently selected in the combo box
* `setLayer(layer)`: set the current layer in the combo box (layer can be a layer or a layer id).

The LayerCombo will also emit signals:

* `layerChanged()` and `layerChangedLayer(QgsMapLayer)`: whenever the layer changes.


## Field combos

A combo box can be assigned to list the fields related to a given VectorLayerCombo.

```python
FieldCombo(widget, vectorLayerCombo, initField="", fieldType=None)
```

* **widget**: the qcombobox widget
* **vectorLayerCombo**: the combobox defining the vector layer
* **initField**: the initially selected field name or a lambda function returning the name (it could look for a value in settings)
* **options**: a dictionnary of options: {"opt1": val1, "opt2": val2, etc.}.

**Options** are listed hereunder, default values being listed first:
* **emptyItemFirst**: True/False. If true, a first empty item is listed first in the combo box.
* **fieldType**: restrain the possible selection to a certain type of field (see [QGIS doc](http://qgis.org/api/classQgsField.html#a00409d57dc65d6155c6d08085ea6c324) or [Qt doc](http://developer.qt.nokia.com/doc/qt-4.8/qmetatype.html#Type-enum)).

This class offer convenient methods:
* `getFieldName()`: returns the name of the currently selected field
* `getFieldAlias()`: returns the alias of the currently selected field
* `getFieldIndex()`: returns the field index of the currently selected field
* `setField(fieldName)`: set the current field in the combo box

The FieldCombo will also emit a signal:

* `fieldChanged()`: whenever the field changes it will emit this signal.

## Band combos

Similarly to field combos, a combo box can be assigned to list the bands related to a given RasterLayerCombo.

```python
BandCombo(widget, rasterLayerCombo, initBand=None)
```
* **widget**: the qcombobox widget
* **rasterLayerCombo**: the combobox defining the raster layer
* **initBand**: the initially selected band (integer) or a lambda function returning it (it could look for a value in settings)

This class offer a convenient method:
* `getBand()`: returns the name of the currently selected band

The BandCombo will also emit a signal:

* `bandChanged(str)`: whenever the band changes it will emit this signal with the new band name.

## Using git submodules

To use this module you can easily copy the files and put them in your project.
A more elegant way is to use [git submodule](http://git-scm.com/book/en/Git-Tools-Submodules). Hence, you can keep up with latest improvements. In you plugin directory, do

```
git submodule add git://github.com/3nids/qgiscombomanager.git
```

A folder _qgiscombomanager_ will be added to your plugin directory. However, git only references the module, and you can `git pull` in this folder to get the last changes.
