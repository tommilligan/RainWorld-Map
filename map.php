<!doctype html>
<head>
<?php 
$xml_raw = file_get_contents('map_tiles/ImageProperties.xml');
$xml_data = simplexml_load_string($xml_raw);
//print_r($xml_data);
?>
<link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.3/leaflet.css" />
<style>
html, body, #map {
    height:100%;
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    background-color: #000000;
}
</style>
</head>
<body>
<div id='map'></div>
<script src="http://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.3/leaflet.js"></script>
<script type='text/javascript' src="scripts/L.TileLayer.Zoomify.js"></script>
<script type='text/javascript'>
var map = L.map('map').setView(new L.LatLng(0,0), 0);
L.tileLayer.zoomify('http://localhost/RainWorld-Map/map_tiles/', {
    width: <?php print((string) $xml_data['WIDTH'])?>,
    height: <?php print((string) $xml_data['HEIGHT'])?>,
    tolerance: 0.8,
    attribution: 'Game: Rain World'
}).addTo(map);
</script>
</body>