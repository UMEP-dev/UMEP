<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.20.3-Odense" maxScale="0" minScale="1e+08" styleCategories="AllStyleCategories" hasScaleBasedVisibilityFlag="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal enabled="0" mode="0" fetchMode="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <customproperties>
    <Option type="Map">
      <Option name="WMSBackgroundLayer" value="false" type="bool"/>
      <Option name="WMSPublishDataSourceUrl" value="false" type="bool"/>
      <Option name="embeddedWidgets/count" value="0" type="int"/>
      <Option name="identify/format" value="Value" type="QString"/>
    </Option>
  </customproperties>
  <pipe>
    <provider>
      <resampling enabled="false" zoomedInResamplingMethod="nearestNeighbour" zoomedOutResamplingMethod="nearestNeighbour" maxOversampling="2"/>
    </provider>
    <rasterrenderer classificationMax="107" opacity="1" nodataColor="" alphaBand="-1" classificationMin="-1" band="1" type="singlebandpseudocolor">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Exact</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader classificationMode="1" labelPrecision="6" clip="0" minimumValue="-1" colorRampType="DISCRETE" maximumValue="107">
          <colorramp name="[source]" type="gradient">
            <Option type="Map">
              <Option name="color1" value="255,255,204,255" type="QString"/>
              <Option name="color2" value="0,104,55,255" type="QString"/>
              <Option name="discrete" value="0" type="QString"/>
              <Option name="rampType" value="gradient" type="QString"/>
              <Option name="stops" value="0.25;194,230,153,255:0.5;120,198,121,255:0.75;49,163,84,255" type="QString"/>
            </Option>
            <prop v="255,255,204,255" k="color1"/>
            <prop v="0,104,55,255" k="color2"/>
            <prop v="0" k="discrete"/>
            <prop v="gradient" k="rampType"/>
            <prop v="0.25;194,230,153,255:0.5;120,198,121,255:0.75;49,163,84,255" k="stops"/>
          </colorramp>
          <item label="no data" value="0" alpha="255" color="#ffffff"/>
          <item label="LCZ 1 comp HR" value="1" alpha="255" color="#8c0004"/>
          <item label="LCZ 2 comp MR" value="2" alpha="255" color="#d10214"/>
          <item label="LCZ 3 comp LR" value="3" alpha="255" color="#ff0000"/>
          <item label="LCZ 4 open HR" value="4" alpha="255" color="#bf4d00"/>
          <item label="LCZ 5 open MR" value="5" alpha="255" color="#ff6600"/>
          <item label="LCZ 6 open LR" value="6" alpha="255" color="#ff9955"/>
          <item label="LCZ 7 light LR" value="7" alpha="255" color="#faee05"/>
          <item label="LCZ 8 large LR" value="8" alpha="255" color="#bcbcbc"/>
          <item label="LCZ 9 sparse " value="9" alpha="255" color="#ffccaa"/>
          <item label="LCZ 10 industry" value="10" alpha="255" color="#555555"/>
          <item label="LCZ 101 dense trees" value="101" alpha="255" color="#006a00"/>
          <item label="LCZ 102 scat trees" value="102" alpha="255" color="#00aa00"/>
          <item label="LCZ 103 bush " value="103" alpha="255" color="#90ae3c"/>
          <item label="LCZ 104 low plant" value="104" alpha="255" color="#bcf0ab"/>
          <item label="LCZ 105 paved" value="105" alpha="255" color="#000000"/>
          <item label="LCZ 106 soil" value="106" alpha="255" color="#fffed2"/>
          <item label="LCZ 107 water" value="107" alpha="255" color="#6a6aff"/>
          <rampLegendSettings suffix="" minimumLabel="" prefix="" maximumLabel="" orientation="2" direction="0" useContinuousLegend="1">
            <numericFormat id="basic">
              <Option type="Map">
                <Option name="decimal_separator" value="" type="QChar"/>
                <Option name="decimals" value="6" type="int"/>
                <Option name="rounding_type" value="0" type="int"/>
                <Option name="show_plus" value="false" type="bool"/>
                <Option name="show_thousand_separator" value="true" type="bool"/>
                <Option name="show_trailing_zeros" value="false" type="bool"/>
                <Option name="thousand_separator" value="" type="QChar"/>
              </Option>
            </numericFormat>
          </rampLegendSettings>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" gamma="1" contrast="0"/>
    <huesaturation grayscaleMode="0" colorizeRed="255" colorizeStrength="100" saturation="-3" colorizeOn="0" colorizeGreen="128" colorizeBlue="128"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
