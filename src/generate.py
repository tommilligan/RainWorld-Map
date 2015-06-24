from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3
import networkx as nx
import math
import sys
import warnings
import argparse
import xml.etree.ElementTree as ET

import common

''' PIXEL DATA
        import numpy as np
        px = np.asarray(screenshot.getdata())
        print px.shape
        '''

subdir_names = ['assets', 'big_image']
directories = common.initialise_subdirs(subdir_names)

DB_LOCATION = common.get_db_path()

MODE = (1, 0)
'''
MODE = (a, b)
a: 0=width, 1=depth (order in which initial positions are calculated)
'''

# even numbers are best
LABEL_IMAGE_DIR = os.path.join(directories[0], 'labels')
MISSING_SCRN_OVERLAY_PATH = os.path.join(directories[0], 'misc', 'rain_mask.png')
TRANSPARENT_PIXEL_PATH = os.path.join(directories[0], 'misc', 'semi.png')
        
def region_property(region_key, property):
        conn = sqlite3.connect(DB_LOCATION)
        region_cursor = conn.cursor()
        region_cursor.execute('SELECT * FROM regions WHERE key = ?', (region_key,))
        value = region_cursor.fetchone()
        headers = region_cursor.description
        for i, h in enumerate(headers):
            if h[0] == property:
                return value[i]

def sentence_to_tuple(val_list):
    val_tuple = tuple(int(x) for x in val_list.split())
    return val_tuple
            
def generate_palette(palette_name, region_key, scale=1.0):
    # Default palette
    values = {'title': (255, 255, 255),
              'bg': (0, 0, 0),
              'detail': (100, 100, 100),
              'skeleton': False,
              'icon': (200, 200, 200),
              'skeleton_line': False,
              'node_labelling': False,
              'detail_line': 16,
              'font_size': 128,
              'font_path': os.path.join(directories[0], 'misc', 'saxmono.ttf'),
              'icon_scale': 1.0,
              'label_image_inset': 100,
              'label_image_spacing': 20,
              'image_padding': 4056
              }
    
    # Overwrite defaults with new color schemes as required
    if palette_name == 'seamless':
        # Get relevant values for each region from DB
        values.update({'title': sentence_to_tuple(region_property(region_key, 'rgb_highlight')),
                       'bg': sentence_to_tuple(region_property(region_key, 'rgb_edge')),
                       'detail': tuple([int(min(255, float(x)*1.5)) for x in sentence_to_tuple(region_property(region_key, 'rgb_bg'))]),
                       'icon': sentence_to_tuple(region_property(region_key, 'rgb_lowlight')+' 175'),
                       'font_size': 256,
                       'icon_scale': 3.0
                       })
    elif palette_name == 'neon':
        values.update({'title': (255, 0, 102),
                       'bg': tuple([int(float(x)/2) for x in sentence_to_tuple(region_property(region_key, 'rgb_edge'))]),
                       'detail': (0, 102, 255),
                       'icon': (0, 255, 102, 175),
                       'icon_scale': 2.0,
                       'label_image_inset': 40,
                       'label_image_spacing': 50
                       })
    elif palette_name == 'debug':
        values.update({'title': (0, 188, 195),
                       'bg': (50, 0, 50),
                       'detail': (255, 0, 0),
                       'icon': (0, 255, 0),
                       'skeleton': (255, 255, 0),
                       'node_labelling': True,
                       'skeleton_line': 16,
                       'detail_line': 24,
                       'font_size': 196,
                       'icon_scale': 3.0
                       })
    
    # Scale to image
    for key, val in values.iteritems():
        if isinstance(val, int):
            values.update({key: int(math.ceil(float(val)*scale))})
        elif isinstance(val, float):
            values.update({key: val*scale})
    
    return values

def label_line_topleft(scrn, x, line_offset=(0,0)):
    return tuple([scrn[y]+(line_offset[y]*x) for y in range(2)])

def invert_rgb(rgb):
    return tuple([255-rgb[x] for x in range(3)])

def draw_network(draw, graph, position_dict, weight=16, color=(127, 127, 127), node_labelling=False, hq_position=(0, 0)):
    '''Takes an ImageDraw object, and uses it to draw a network as held by a networkx graph object & the node property 'position_dict' containing a (x,y) location tuple'''
    '''Will label nodes if labelling is given as a Pillow font object'''
    # Only draw if weight > 0
    if weight > 0:
        for edge in graph.edges():
            adj_start = tuple([graph.node[edge[0]][position_dict][x]-hq_position[x] for x in range(2)])
            adj_fin = tuple([graph.node[edge[1]][position_dict][x]-hq_position[x] for x in range(2)])
            draw.line([adj_start, adj_fin], fill=color, width=weight)
        def_font = ImageFont.load_default()
        for node in graph.nodes():
            adj_tl = tuple(graph.node[node][position_dict][x]-hq_position[x]-weight*2 for x in range(2))
            adj_br = tuple(graph.node[node][position_dict][x]-hq_position[x]+weight*2 for x in range(2))
            draw.ellipse([adj_tl, adj_br], fill=color, outline=color)
            if node_labelling:
                text_pos = tuple([adj_tl[x]-1*(adj_br[x]-adj_tl[x]) for x in range(2)])
                draw.text(text_pos, str(node), font=def_font, fill=color)
    return None  

def change_color(mask, color):
    '''Takes an RGBA image and changes it's color to the given RGBA tuple format color, maintaining the original alpha values'''
    mask = mask.convert(mode='RGBA')
    overlay = Image.new('RGBA', mask.size, color=color)
    mask.paste(overlay, box=(0,0), mask=mask)
    return mask
    
def get_area_screenshot(area, image_scale_factor=1):
    screenshot_path = os.path.join(directories[0], 'areas', str(area)+'.jpg')
    to_return = None
    if os.path.isfile(screenshot_path):
        original = Image.open(screenshot_path)
        to_return = original.convert(mode="RGBA")
    # if no screenshot, put in placeholder rain image
    else:
        mask = Image.open(MISSING_SCRN_OVERLAY_PATH)
        to_return = change_color(mask, (255, 255, 255, 159))
        
    if image_scale_factor != 1.0:
        to_return = to_return.resize(tuple([int(to_return.size[x]*image_scale_factor) for x in range(2)]))
    
    return to_return

def draw_map(region_key, palette_name='default', image_scale_factor=1, network_contraction=3, network_overlap=3, draw_world=False, iterations=50):
    '''Hard-coded params - replace if possible'''
    RAW_SCREENSHOT_SIZE = (1366, 768) # Roug size per image, used to estimate the size of the total image required
    HQ_TILE_LEVEL = 5 # The level at which to split into multiple hq tiles
    metadata_file_name = 'ImageProperties.xml'
    ''''''
    
    image_palette = generate_palette(palette_name, region_key, scale=image_scale_factor)
    line_offset = (int(image_palette['font_size']/2), -1*(image_palette['font_size']+6))
    font = ImageFont.truetype(font=image_palette['font_path'], size=image_palette['font_size'])
    
    conn = sqlite3.connect(DB_LOCATION)
    region_cursor = conn.cursor()
    region_cursor.execute('SELECT key, name, default_area FROM regions WHERE key = ?', (region_key,))
    region = region_cursor.fetchone()
    print '>', region[1].upper()
    print '>> Calculating network'
    initial_area = None
    if region[2]:
        initial_area = region[2]
    else:
        area_cursor = conn.cursor()
        area_cursor.execute('SELECT key FROM areas WHERE region = ? ORDER BY key ASC', (region[0],))
        initial_area = area_cursor.fetchone()[0]
        if not initial_area:
            print 'Region has no areas'
            return False
    # Initialise graph, and add area with lowest id as the origin room
    G = nx.Graph()
    G.add_node(initial_area)
    G.node[initial_area]['pos_rough'] = (0, 0)
    pos_rough = {initial_area: (0, 0)}
    pos_to_expand = [initial_area]
    
    # as areas are found, add them to a list to be searched, and search them
    while len(pos_to_expand) > 0:
        # Order in which area initial positions are calculated
        area = None
        if MODE[0] == 0:
            area = pos_to_expand.pop(0)
        elif MODE[0] == 1:
            area = pos_to_expand.pop()
        else:
            sys.exit('Invalid MODE specified')
        
        # for each linking area (SQL lookup)
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key FROM nodes WHERE area = ? ORDER BY key ASC', (area,))
        for node in node_cursor:
            # look up link_node key (and link_node's area key)
            link_cursor = conn.cursor()
            link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
            link_node = link_cursor.fetchone()
            #if link_node is specified and exists
            if link_node:
                # lookup linked area and region
                link_cursor = conn.cursor()
                link_cursor.execute('SELECT region FROM areas WHERE key = ?', (link_node[2],))
                link_region = link_cursor.fetchone()
                if link_region:
                    # If linked area is in same region OR world-map flag is set, add to list of areas to expand upon
                    if (link_region[0] == region_key) or draw_world:
                        # if link_node's area key not in pos list
                        if link_node[2] not in pos_rough:
                            # add to graph as node
                            G.add_node(area)
                            # calculate a relative position for new area from initial area
                            relative_px = tuple(node[x]-link_node[x] for x in range(2))
                            # store this as as an absolute set of coordinates
                            absolute_px = tuple(pos_rough[area][x]+relative_px[x] for x in range(2))
                            # add room to pos list (key, (x_pos, y_pos))
                            pos_rough.update({link_node[2] : absolute_px})
                            # add rom to list of rooms to search from next
                            pos_to_expand.append(link_node[2])
                        
                        # add edge even if position already set
                        G.add_edge(area, link_node[2])
                    
                else:
                    print '! Linked region '+str(link_node[2])+' not found in areas list'
                    return False
    
    pos_spring = {}
    # optimise node positions using Fruchterman-Reingold force-directed algorithm
    # iterations=1 will format values to the standard output, but not actually optimise positions
    opt_dist_default = 1/math.sqrt(len(pos_rough))
    opt_dist = opt_dist_default/network_contraction
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # WARNING pos_spring generates a numpy based FutureWarning
        if iterations <= 0:
            iterations = 1
        pos_spring = nx.spring_layout(G, pos=pos_rough, k=opt_dist, iterations=iterations)
    
    # pull pos_spring optimised values into networkx object
    for key in G.nodes():
        G.node[key]['pos_spring'] = pos_spring[key]
    
    # make image using positions given
    ROUGH_SCREENSHOT_SIZE = tuple([int(RAW_SCREENSHOT_SIZE[x]*image_scale_factor) for x in range(2)])
    SCALE = int(max(ROUGH_SCREENSHOT_SIZE)*math.sqrt(len(G.nodes()))*network_overlap)
    image_size_init = tuple([SCALE+image_palette['image_padding'] for x in range(2)])

    # convert pos_spring (0-1 space) to image space (px)
    image_origin = tuple(int(math.floor(image_size_init[x]/2)) for x in range(2))
    for key in G.nodes():
        G.node[key]['pos_px'] = tuple(math.floor((G.node[key]['pos_spring'][x]-0.5)*SCALE)+image_origin[x] for x in range(2))
    
    #initialised detailed node graph for position collection
    H = nx.Graph()
    
    #Read data from database and image files into networkx object for later drawing
    for key in G.nodes():
        pos = G.node[key]['pos_px']
        label_cursor = conn.cursor()
        label_cursor.execute('SELECT name, type FROM areas WHERE key = ?', (key,))
        label = label_cursor.fetchone()
        G.node[key]['name'] = label[0].upper()
        #print '>>> Area', key, G.node[key]['name']
        
        screenshot_path = os.path.join(directories[0], 'areas', str(area)+'.jpg')
        G.node[key]['screenshot'] = get_area_screenshot(key, image_scale_factor=image_scale_factor)
        G.node[key]['pos_topleft_px'] = tuple(int(math.floor(pos[x]-G.node[key]['screenshot'].size[x]/2)) for x in range(2))
        
        #detail edges added to graph & dict objects to be drawn later
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key, key FROM nodes WHERE area = ? ORDER BY key ASC', (key,))
        for node in node_cursor:
            # if node is not already in detail_graph
            if not H.has_node(node[3]):
                #add node to detailed graph and store position
                H.add_node(node[3])
                node_pos = tuple([pos[x]+node[x]*image_scale_factor for x in range(2)])
                H.node[node[3]]['pos_detail_px'] = node_pos
                # look up connecting node id -> area id
                link_cursor = conn.cursor()
                link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
                link_node = link_cursor.fetchone()
                # add connecting node and edge (if node available)
                if link_node:
                    if link_node[2] in G.nodes():
                        H.add_node(node[2])
                        H.add_edge(node[2], node[3])
                        link_area_pos = G.node[link_node[2]]['pos_px']
                        link_node_pos = tuple([link_area_pos[x]+link_node[x]*image_scale_factor for x in range(2)])
                        H.node[node[2]]['pos_detail_px'] = link_node_pos
        # save room type
        if label[1]:
            G.node[key]['type'] = label[1]
        else:
            G.node[key]['type'] = None
    
    #Drawing
    # New image errors above arbitrary size (OS limit on single process memory ~2gb)
    #To avoid causing a MemoryError, the map is drawn in hq tiles of 8192px (256**5) maximum edge length
    hq_tile_size = 256*2**HQ_TILE_LEVEL
    images_required = tuple([int(math.ceil(float(image_size_init[x])/float(hq_tile_size))) for x in range(2)])
    print '>> Total image size:', str(image_size_init[0])+'x'+str(image_size_init[1])+', splitting to', images_required[0]*images_required[1], str(hq_tile_size)+'x'+str(hq_tile_size),'hq image tiles' 
    
    region_dir = os.path.join(directories[1], region[1].replace(' ', '_'))
    user_check = common.renew_dir(region_dir)
    if user_check is not True:
        return False
    
    #row strips
    for row in range(images_required[1]):
        #col strips
        for col in range(images_required[0]):
            hq_name = 'hq-'+str(col)+'-'+str(row)+'.png'
            hq_position = tuple([hq_tile_size*col, hq_tile_size*row])
            hq_spec = ([min(hq_position[x]+hq_tile_size, image_size_init[x])-hq_position[x] for x in range(2)])
            with warnings.catch_warnings():
                # WARNING Image.new generates a DecompressionBomb warning with large file sizes
                warnings.simplefilter("ignore")
                big_image = Image.new('RGBA', hq_spec, color=image_palette['bg'])
            big_draw = ImageDraw.Draw(big_image)
            
            #drawings layered in desired order - later will be on top
            #draw screenshots onto image
            for key in G.nodes():
                if G.node[key]['name']:
                    box_adj = tuple([G.node[key]['pos_topleft_px'][x]-hq_position[x] for x in range(2)])
                    big_image.paste(G.node[key]['screenshot'], box=box_adj, mask=G.node[key]['screenshot'])
            
            #draw skeleton edges if color specified in palette
            if image_palette['skeleton']:
                draw_network(big_draw, G, 'pos_px',  weight=image_palette['skeleton_line'], color=image_palette['skeleton'], node_labelling=image_palette['node_labelling'], hq_position=hq_position)
                   
            #draw detail edges
            draw_network(big_draw, H, 'pos_detail_px', weight=image_palette['detail_line'], color=image_palette['detail'], node_labelling=image_palette['node_labelling'], hq_position=hq_position)
            
            #draw labels and icons
            for key in G.nodes():
                if G.node[key]['type']:
                    label_list = sorted(G.node[key]['type'].split(), reverse=True)
                    label_text = str('/'.join(label_list)+' room').upper()
                    adj_topleft_px = tuple([G.node[key]['pos_topleft_px'][x]-hq_position[x] for x in range(2)])
                    big_draw.text(label_line_topleft(adj_topleft_px, 2, line_offset), label_text, font=font, fill=image_palette['icon'])
                    label_col_current_height = 0+image_palette['label_image_spacing']
                    for label in label_list:
                        # Load icon mask
                        label_path = os.path.join(LABEL_IMAGE_DIR, label+'.png')
                        if os.path.isfile(label_path):
                            label_mask = Image.open(label_path)
                            label_mask = label_mask.resize(tuple([int(label_mask.size[x]*image_palette['icon_scale']) for x in range (2)]))
                            label_mask = change_color(label_mask, image_palette['icon']) 
                            # Centre labels and add padding
                            label_topleft = tuple([int(G.node[key]['pos_topleft_px'][0]+image_palette['label_image_inset']-(0.5*label_mask.size[0]))-hq_position[0], int(G.node[key]['pos_topleft_px'][1]+label_col_current_height)-hq_position[1]])
                            big_image.paste(label_mask, box=label_topleft, mask=label_mask)
                            label_col_current_height = label_col_current_height+image_palette['label_image_spacing']+label_mask.size[1]
            
            #draw titles
            for key in G.nodes():
                if G.node[key]['name']:
                    text = G.node[key]['name']
                    if palette_name == 'debug':
                        text = text+' ('+str(key)+')'
                    adj_topleft_px = tuple([G.node[key]['pos_topleft_px'][x]-hq_position[x] for x in range(2)])
                    big_draw.text(label_line_topleft(adj_topleft_px, 1, line_offset), text, font=font, fill=image_palette['title'])
            
            # save
            print '>> Saving', hq_name
            big_image_path = os.path.join(region_dir, hq_name)
            big_image.save(big_image_path, quality=100)
    
    # Write XML metadata file
    root = ET.Element('IMAGE_PROPERTIES')
    root.attrib = {'WIDTH': str(image_size_init[0]),
                   'HEIGHT': str(image_size_init[1]),
                   'NUMTILES': str(images_required[0]*images_required[1]),
                   'NUMIMAGES': str(1),
                   'TILESIZE': str(hq_tile_size)
                   }
    tree = ET.ElementTree(root)
    tree.write(os.path.join(region_dir, metadata_file_name))
    return region_dir # Return directory path of saved images

def main():       
    print 'This script should not be called directly'
        
if __name__ == '__main__':
    main()