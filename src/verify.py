import os
import sys
import sqlite3

import common

DB_LOCATION = common.get_db_path()

print '\n>> Verification started\n'

# Check for duplicate id numbers
def allUnique(x):
    seen = list()
    for i in x:
        if i in seen:
            return i
        else:
            seen.append(i)
    else:
        return None

conn = sqlite3.connect(DB_LOCATION)
region_cursor = conn.cursor()
region_cursor.execute('SELECT key FROM regions ORDER BY key ASC')
for region in region_cursor:
    area_cursor = conn.cursor()
    area_cursor.execute('SELECT key FROM areas WHERE region = ? ORDER BY key ASC', (region[0],))
    areas = area_cursor.fetchall()
    areas_check = allUnique(areas)
    if areas_check:
        msg = 'Error in region '+str(region[0])+'; duplicate area '+str(areas_check)
        print msg
    for area in areas:
        node_cursor = conn.cursor()
        node_cursor.execute('SELECT key FROM nodes WHERE area = ? ORDER BY node ASC', (area[0],))
        nodes = node_cursor.fetchall()
        nodes_check = allUnique(nodes)
        if nodes_check:
            msg = 'Error in area '+str(area[0])+'; duplicate node '+str(nodes_check)
            print msg

# Check that all connections backlink (i.e. point to each other)
# Contingent on there being no duplications (as tested above)
link_cursor = conn.cursor()
link_cursor.execute('SELECT key, link_key FROM nodes ORDER BY key ASC')
links_checked = list()
for link in link_cursor:
    revlink_cursor = conn.cursor()
    revlink_cursor.execute('SELECT link_key FROM nodes WHERE key = ?', (link[1],))
    revlink = revlink_cursor.fetchone()
    if revlink:
        if link[0] != revlink[0]:
            msg = 'Nodes incorrectly linked: '+str(link[0])+' to '+str(link[1])+' to '+str(revlink[0])
            print msg
    else:
        msg = 'Linked node does not exist: ' +str(link[0])+' to '+str(link[1])
        print msg

print '\n>> Verification complete\n'