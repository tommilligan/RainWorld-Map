from PIL import Image
import os
import math

TILE_SIZE = 256 # must be integer

def divisions_required(total_length, sub_length):
    precise = total_length/sub_length
    if total_length%sub_length == 0:
        precise = precise-1
    return int(math.ceil(precise)+1)

# Open image and determine size, tiles and zoom levels required
input_path = 'C:/Users/Thomas/Documents/Code/RainWorld-Map/RainWorld-Map/z_input/RainWorld-Map.jpg'
big_image = Image.open(input_path)
max_divisions_required = max(divisions_required(big_image.size[0], TILE_SIZE), divisions_required(big_image.size[1], TILE_SIZE))
max_zoom_level = int(math.ceil(math.log(max_divisions_required, 2)))
print big_image.size

# Tile Generation
# Zoom level
for loop_zoom in xrange(0, int(max_zoom_level)):
    area_size_multiplier = 2**(max_zoom_level-1-loop_zoom)
    area_side_length = TILE_SIZE*area_size_multiplier
    rows_required = divisions_required(big_image.size[1], area_side_length)
    cols_required = divisions_required(big_image.size[0], area_side_length)
    area_resize_ratio = TILE_SIZE/area_side_length
    print str(loop_zoom)+'#'+str(area_side_length)
    # Each row
    for loop_row in xrange(0, int(rows_required)):
        tile_origin_y = loop_row*area_side_length
        # Columns in row
        for loop_col in xrange(0, int(cols_required)):
            tile_origin_x = loop_col*area_side_length
            box = (tile_origin_x,
                   tile_origin_y,
                   min(tile_origin_x+area_side_length, big_image.size[0]),
                   min(tile_origin_y+area_side_length, big_image.size[1])
                   )
            # Calculate size of tile to save
            area_size_actual = (box[2]-box[0], box[3]-box[1])
            area_resize = tuple(d/area_size_multiplier for d in area_size_actual)
            print str(loop_row)+','+str(loop_col)+'#'+str(box)
            # Crop, resize and save tile
            tile_raw = big_image.crop(box)
            tile_resampled = tile_raw.resize(area_resize)
            tile_id = str(loop_zoom)+'-'+str(loop_col)+'-'+str(loop_row);
            tile_save_path = 'C:/Users/Thomas/Documents/Code/RainWorld-Map/RainWorld-Map/z_output/'+tile_id+'.jpg'
            tile_resampled.save(tile_save_path)

