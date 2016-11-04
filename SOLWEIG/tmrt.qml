<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="2.16.3" minimumScale="100000" maximumScale="1e+08" hasScaleBasedVisibilityFlag="0">
  <pipe>
    <rasterrenderer opacity="1" alphaBand="0" classificationMax="70" classificationMinMaxOrigin="User" band="1" classificationMin="-10" type="singlebandpseudocolor">
      <rasterTransparency/>
      <rastershader>
        <colorrampshader colorRampType="INTERPOLATED" clip="0">
          <item alpha="255" value="-10" label="-10" color="#2c7bb6"/>
          <item alpha="255" value="10" label="10" color="#abd9e9"/>
          <item alpha="255" value="30" label="30" color="#ffffbf"/>
          <item alpha="255" value="50" label="50" color="#fdae61"/>
          <item alpha="255" value="70" label="70" color="#d7191c"/>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0"/>
    <huesaturation colorizeGreen="128" colorizeOn="0" colorizeRed="255" colorizeBlue="128" grayscaleMode="0" saturation="0" colorizeStrength="100"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
