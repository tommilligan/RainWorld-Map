from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3
import networkx as nx
import math
import sys

import common

directories = common.initialise_subdirs(['assets', 'big_image'])
DB_LOCATION = common.get_db_path()

'''
MODE = (a, b)
a: 0=width, 1=depth (order in which initial positions are calculated)
b: 0=final, 1=continuous (how ofter spring_layout is calculated)
'''
MODE = (1, 0)

# even numbers are best
BACKGROUND_COLOR = (26, 11, 32)
SCREENSHOT_SIZE = (1366, 768)
IMAGE_PADDING = 500
NODE_SIZE = 16
NODE_PADDING = 4
LABEL_LINE_HEIGHT = 25
LABEL_LINE_OFFSET = 15
LABEL_IMAGE_OFFSET = (20, 20)
LABEL_IMAGE_BOUNDS = (100, 100)
SKELETON_COLOR = (255, 0, 102)
DETAIL_COLOR = (0, 255, 102)
SKELETON_LINE_WIDTH = 2
DETAIL_LINE_WIDTH = 6

# Take location of screenshot and xth line, and return position. If x = 0 returns scrn
def label_line_topleft(scrn, x):
    return tuple([scrn[0]+(LABEL_LINE_OFFSET*x), scrn[1]-(LABEL_LINE_HEIGHT*x)])

def invert_rgb(rgb):
    return tuple([255-rgb[x] for x in range(3)])

conn = sqlite3.connect(DB_LOCATION)
region_cursor = conn.cursor()
region_cursor.execute('SELECT key, name FROM regions ORDER BY key ASC')
regions = region_cursor.fetchall()
# print region maps separately
for region in regions:
    print '>', region[1]
    area_cursor = conn.cursor()
    area_cursor.execute('SELECT key FROM areas WHERE region = ? ORDER BY key ASC', (region[0],))
    initial_area = area_cursor.fetchone()
    
    # Initialise graph, and add area with lowest id as the origin room
    G = nx.Graph()
    G.add_node(initial_area[0])
    pos_rough = {initial_area[0]: (0, 0)}
    pos_to_expand = [initial_area[0]]
    # for each area in pos list
    #for area, position in pos_rough.iteritems():
    while len(pos_to_expand) > 0:
        # Order in which area initial positions are calculated
        if MODE[0] == 0:
            area = pos_to_expand.pop(0)
        elif MODE[0] == 1:
            area = pos_to_expand.pop()
        else:
            sys.exit('Invalid MODE specified')
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key FROM nodes WHERE area = ? ORDER BY key ASC', (area,))
        # for each linking area (SQL lookup)
        for node in node_cursor:
            # look up connecting node id -> area id
            link_cursor = conn.cursor()
            link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
            link_node = link_cursor.fetchone()
            # if linking area not in pos list
            if link_node[2] not in pos_rough:
                # add to graph as node
                G.add_node(area)
                # calculate an initial position for room from initial room
                relative_px = tuple(node[x]-link_node[x] for x in range(2))
                absolute_px = tuple(pos_rough[area][x]+relative_px[x] for x in range(2))
                # add room to pos list (key, (x_pos, y_pos))
                pos_rough.update({link_node[2] : absolute_px})
                # if same region (NOT region-gate), further search needed, add to pos_to_expand
                link_cursor = conn.cursor()
                link_cursor.execute('SELECT region FROM areas WHERE key = ?', (link_node[2],))
                link_region = link_cursor.fetchone()
                if link_region[0] == region[0]:
                    pos_to_expand.append(link_node[2])
            else:
                None
            # add edge whether area already has position or not
            G.add_edge(area, link_node[2])
            if MODE[1] == 0:
                None
            # continuous adjustment during addition
            elif MODE[1] == 1:
                pos_rough = nx.spring_layout(G, pos=pos_rough)
            else:
                sys.exit('Invalid MODE specified')
                    
    # optimise node positions using Fruchterman-Reingold force-directed algorithm
    pos_spring = nx.spring_layout(G, pos=pos_rough)
    
    # make image using positions given
    SCALE = int((max(SCREENSHOT_SIZE)*len(G.nodes()))/2)
    image_size_init = (SCALE+IMAGE_PADDING*4, SCALE+IMAGE_PADDING*2)
    image_origin = tuple(math.floor(image_size_init[x]/2) for x in range(2))
    # scale up coords to image size and centre (origin)
    pos_px = {key: tuple(math.floor((pos[x]-0.5)*SCALE)+image_origin[x]
              for x in range(2))
              for key, pos in pos_spring.iteritems()
              }
    big_image = Image.new('RGB', image_size_init, color=BACKGROUND_COLOR)
    big_draw = ImageDraw.Draw(big_image)
    font = ImageFont.load_default()
    
    # draw nodes
    '''
    look at scale|spring k value for overlapping nodes?
    '''
    print 'Collating'
    for key, pos in pos_px.iteritems():
        label_cursor = conn.cursor()
        label_cursor.execute('SELECT name, type FROM areas WHERE key = ?', (key,))
        label = label_cursor.fetchone()
        label_name = label[0].upper()
        print '> Area', key, label_name
        screenshot = Image.open(os.path.join(directories[0], 'areas', str(key)+'.jpg'))
        screenshot_topleft = tuple(int(math.floor(pos[x]-SCREENSHOT_SIZE[x]/2)) for x in range(2))
        big_image.paste(screenshot, box=screenshot_topleft)
        big_draw.text(label_line_topleft(screenshot_topleft, 1), label_name+' ('+str(key)+')', font=font)
        if label[1]:
            label_list = sorted(label[1].split())
            label_text = str(', '.join(label_list)+' room').upper()
            big_draw.text(label_line_topleft(screenshot_topleft, 2), label_text, font=font)
            for y in range(len(label_list)):
                # Get colour of image bg
                px = screenshot.load()
                screenshot_px_topleft = px[0,0]
                label_mask = Image.open(os.path.join(directories[0], 'tags', label_list[y]+'.png'))
                label_size = label_mask.size
                label_image = Image.new('RGB', label_size, color=invert_rgb(screenshot_px_topleft)) 
                # Centre labels and add padding
                label_topleft = tuple([int(screenshot_topleft[x]+LABEL_IMAGE_OFFSET[x]+0.5*(LABEL_IMAGE_BOUNDS[x]-label_size[x])) for x in range(2)])
                label_topleft = tuple([label_topleft[0], label_topleft[1]+(LABEL_IMAGE_BOUNDS[1]+LABEL_IMAGE_OFFSET[1])*y])
                big_image.paste(label_image, box=label_topleft, mask=label_mask)
        else:
            None
        
        #detail edges
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT x_pos, y_pos, link_key FROM nodes WHERE area = ? ORDER BY key ASC', (key,))
        for node in node_cursor:
            # look up connecting node id -> area id
            link_cursor = conn.cursor()
            link_cursor.execute('SELECT x_pos, y_pos, area FROM nodes WHERE key = ?', (node[2],))
            link_node = link_cursor.fetchone()
            link_area_pos = pos_px[link_node[2]]
            node_pos = tuple([pos[x]+node[x] for x in range(2)])
            link_node_pos = tuple([link_area_pos[x]+link_node[x] for x in range(2)])
            big_draw.line([node_pos, link_node_pos], fill=DETAIL_COLOR, width=DETAIL_LINE_WIDTH)
    
    #skeleton edges
    for edge in G.edges():
        big_draw.line([pos_px[edge[0]], pos_px[edge[1]]], fill=SKELETON_COLOR, width=SKELETON_LINE_WIDTH)

    # save
    print 'Saving'
    big_image_path = os.path.join(directories[1], region[1]+'.png')
    big_image.save(big_image_path, quality=100)
