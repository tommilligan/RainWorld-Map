from PIL import Image
import os
import re
import sys
import math
import glob
import shutil
import argparse
import xml.etree.ElementTree as ET

import common

TILE_SIZE = 256
HQ_TILE_SIZE = 8192
TOP_DIR = common.root_dir()
TILES_PER_SUBDIR = 256
TILE_SUBDIR_PREFIX = 'TileGroup'
METADATA_FILE = 'ImageProperties.xml'

def zoom_level_max_tiles(zoom_level):
    return 2**zoom_level
    
def zoom_level_max_px(zoom_level):
    return zoom_level_max_tiles(zoom_level)*TILE_SIZE

def divisions_required(total_length, sub_length):
    precise = total_length/sub_length
    if total_length%sub_length == 0:
        precise = precise-1
    return int(math.ceil(precise)+1)

def max_zoom_level(size):
    '''size as x,y tuple'''
    max_divisions_required = divisions_required(max(size), TILE_SIZE)
    max_zoom_level = int(math.ceil(math.log(max_divisions_required, 2)+1))
    return max_zoom_level
    
def zoomify_order(image_size, output_dir):
    '''image_size must be tuple in (x, y) format, output_dir must be string'''
    print '>> Moving files'
    tiles_moved = 0
    max_zoom = max_zoom_level(image_size)
    for loop_zoom in xrange(0, int(max_zoom)):
        area_size_multiplier = 2**(max_zoom-1-loop_zoom)
        area_side_length = TILE_SIZE*area_size_multiplier
        rows_required = divisions_required(image_size[1], area_side_length)
        cols_required = divisions_required(image_size[0], area_side_length)
        # Each row
        for loop_row in xrange(0, int(rows_required)):
            tile_origin_y = loop_row*area_side_length
            # Columns in row
            for loop_col in xrange(0, int(cols_required)):
                tile_id = str(loop_zoom)+'-'+str(loop_col)+'-'+str(loop_row)
                tile_subdir_suffix = str(int(math.floor(tiles_moved/TILES_PER_SUBDIR)))
                tile_subdir = os.path.join(output_dir, TILE_SUBDIR_PREFIX+tile_subdir_suffix)
                common.make_dir_if_not_found(tile_subdir)
                current_path = os.path.join(output_dir, tile_id+'.jpg')
                destination_path = os.path.join(tile_subdir, tile_id+'.jpg')
                try:
                    shutil.move(current_path, destination_path)
                except IOError:
                    continue
                tiles_moved = tiles_moved+1
    return tiles_moved
    
def zoomify_slice(big_image, max_zoom_level, output_dir, min_zoom_level=0, offset=(0, 0), tilesize=0):
    '''big_image is an image object containing the image to be tiled
        max_zoom_level indicates how many zoom levels are required (important for directories)
        output_dir is the top dir for output
        offset is used to indicate the position of this slice in directory processing'''
    #Zoom level
    for loop_zoom in xrange(min_zoom_level, int(max_zoom_level)):
        #if loop_zoom < 0: continue 
        area_size_multiplier = 2**(max_zoom_level-1-loop_zoom)
        area_side_length = TILE_SIZE*area_size_multiplier
        rows_required = divisions_required(big_image.size[1], area_side_length)
        cols_required = divisions_required(big_image.size[0], area_side_length)
        area_resize_ratio = TILE_SIZE/area_side_length
        print '>>>', str(loop_zoom)+'#'+str(area_side_length)
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
                # Calculate details of tile to save
                area_size_actual = (box[2]-box[0], box[3]-box[1])
                area_resize = tuple(d/area_size_multiplier for d in area_size_actual)
                # 
                tile_id = str(loop_zoom)+'-'+str(loop_col+(offset[0]*divisions_required(tilesize, area_side_length)))+'-'+str(loop_row+(offset[1]*divisions_required(tilesize, area_side_length)))
                tile_save_path = os.path.join(output_dir, tile_id+'.jpg')
                
                # Crop, resize and save tile
                tile_raw = big_image.crop(box)
                tile_resampled = tile_raw.resize(area_resize)
                tile_resampled.save(tile_save_path)
    return None

def zoomify_lowres_composite(min_zoom_level, max_zoom_level, image_size, output_dir):
    '''Designed to provide low-res composites of the lower level zoom levels, from previously generated .jpg tiles in the layer below (only for directory processing'''
    print '>> Compositing zoom layer', min_zoom_level, 'to generate low-res tiles'
    # Area length max of min_zoom_level
    area_side_length = zoom_level_max_px(min_zoom_level)
    dim_required = divisions_required(area_side_length, TILE_SIZE)
    # Make canvas next zoom level down from the min_zoom_level already generated
    canvas_size = tuple([int((image_size[x]/(2**max_zoom_level))*(2**(min_zoom_level+1))) for x in range(2)])
    canvas = Image.new('RGBA', canvas_size, color=(255, 255, 255))
    # Each row
    for loop_row in xrange(0, dim_required):
        # Columns in row
        for loop_col in xrange(0, dim_required):
            lq_path = os.path.join(output_dir, str(min_zoom_level)+'-'+str(loop_col)+'-'+str(loop_row)+'.jpg')
            try:
                lq = Image.open(lq_path)
            except IOError:
                None
            canvas.paste(lq, box=(loop_col*TILE_SIZE, loop_row*TILE_SIZE))
    downscaled_size = tuple([int((image_size[x]/(2**max_zoom_level))*(2**(min_zoom_level))) for x in range(2)])
    downscaled = canvas.resize(downscaled_size)
    zoomify_slice(downscaled, min_zoom_level, output_dir)
    return None
    
def zoomify(path, output_dir):
    print '> Zoomifying', path
    # Write XML metadata file
    root = ET.Element('IMAGE_PROPERTIES')
    tiles_moved = 0
    
    #if path points to hq-format directory
    if os.path.isdir(path):
        metadata_path = os.path.join(path, METADATA_FILE)
        if os.path.isfile(metadata_path):
            file_dir = os.path.join(output_dir, os.path.basename(os.path.normpath(path)).replace(' ', '_'))
            user_check = common.renew_dir(file_dir)
            if user_check is not True:
                return False
            tree_read = ET.parse(metadata_path)
            root_read = tree_read.getroot()
            # Trasform to integer values for use
            meta = {key: int(val) for key, val in root_read.attrib.iteritems()}
            rows = divisions_required(meta['HEIGHT'], meta['TILESIZE'])
            cols = divisions_required(meta['WIDTH'], meta['TILESIZE'])
            meta_size = tuple([meta['WIDTH'], meta['HEIGHT']])
            # The max zoom needed to generate a single hq_tile at original resolution
            hq_zoom_range = int(math.ceil(math.log(meta['TILESIZE']/256, 2))+1) #+1
            # The max zoom needed to generate the whole image at original resolution
            hq_zoom_max = max_zoom_level(meta_size)
            # The zoom levels missing, that will need to be composited after initial zoomification needed to generate the whole image at original resolution
            hq_zoom_min = max(0, hq_zoom_max-hq_zoom_range)
            '''add this as file prefix z_level? str(hq_zoom_level)'''
            # Each row
            for loop_row in xrange(0, int(rows)):
                # Columns in row
                for loop_col in xrange(0, int(cols)):
                    tile_id = 'hq'+'-'+str(loop_col)+'-'+str(loop_row)
                    tile_open_path = os.path.join(path, tile_id+'.png')
                    hq_offset = (loop_col, loop_row)
                    print '>>', tile_id
                    hq_tile = Image.open(tile_open_path)
                    zoomify_slice(hq_tile, hq_zoom_max, file_dir, min_zoom_level=hq_zoom_min, offset=hq_offset, tilesize=meta['TILESIZE'])
            if hq_zoom_min > 0:
                zoomify_lowres_composite(hq_zoom_min, hq_zoom_max, meta_size, file_dir)
            tiles_moved = zoomify_order(meta_size, file_dir)
            #Set metadata attributes
            root.attrib.update({'WIDTH': root_read.attrib['WIDTH'],
                               'HEIGHT': root_read.attrib['HEIGHT'],
                               })
        else:
            print 'No metadata file found at', metadata_path
            return False
 
    #if just single image file
    else:
        file_prefix = str(os.path.split(path)[1]).split('.')
        file_dir = os.path.join(output_dir, file_prefix[0].replace(' ', '_'))
        common.make_dir_if_not_found(file_dir)
        # Open image and determine size, tiles and zoom levels required
        input_path = os.path.join(path)
        print '>> Single image'
        big_image = Image.open(input_path)

        # Tile Generation
        max_zoom = max_zoom_level(big_image.size)
        zoomify_slice(big_image, max_zoom, file_dir)
        tiles_moved = zoomify_order(big_image.size, file_dir)
        
        #Set metadata attributes
        root.attrib.update({'WIDTH': str(big_image.size[0]),
                           'HEIGHT': str(big_image.size[1]),
                           })
    
    root.attrib.update({'NUMTILES': str(tiles_moved),
                       'NUMIMAGES': str(1),
                       'VERSION': '1.8',
                       'TILESIZE': str(TILE_SIZE)
                       })
    tree = ET.ElementTree(root)
    tree.write(os.path.join(file_dir, METADATA_FILE))
    print '>> '+root.attrib['WIDTH']+'x'+root.attrib['HEIGHT']+' image saved as '+root.attrib['NUMTILES'], root.attrib['TILESIZE']+'px tiles in '+str(int(math.ceil(float(root.attrib['NUMTILES'])/float(TILES_PER_SUBDIR))))+' subdirectories'
'''
def main():
    # Default in and out directories
    directories = common.initialise_subdirs(['big_image', 'zoomify_tiles'])

    parser = argparse.ArgumentParser(description='Make big map image from screenshots and connection data') #Parse arguments 
    parser.add_argument('-i', '--input', default=None,
                        help='Input file or direcory. Default is all subdirs of "../'+directories[0]+'"')
    parser.add_argument('-o', '--output', default=None,
                        help='Output direcory. Default is "../'+directories[1]+'"')
    args = parser.parse_args()
    INPUT_PATH = os.path.realpath(os.path.join(os.getcwd(), args.input))
    OUTPUT_PATH = os.path.realpath(os.path.join(os.getcwd(), directories[1]))
    if args.output:
        OUTPUT_PATH = os.path.realpath(os.path.join(os.getcwd(), args.output))  
    
    if INPUT_PATH is None:
        input_files = [os.path.join(directories[0], name) for name in os.listdir(directories[0])]
        if len(input_files) > 0:
            for file_path in input_files:
                zoomify(file_path, OUTPUT_PATH)
        else:
            sys.exit('No valid input images.')
    else:
        zoomify(INPUT_PATH, OUTPUT_PATH)
    
if __name__ == "__main__":
    main()'''