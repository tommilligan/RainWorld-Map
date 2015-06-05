import os
import sys
import sqlite3

import common

DB_LOCATION = common.get_db_path()

print '\n>> Verification started\n'

conn = sqlite3.connect(DB_LOCATION)

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