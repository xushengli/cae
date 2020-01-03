#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
    © Ihor Mirzov, December 2020
    Distributed under GNU General Public License v3.0

    Parses finite element mesh from the CalculiX .inp-file.
    Reads nodes coordinates, elements composition,
    node and element sets and surfaces.
"""


import re, logging
try:
    # Normal run
    import file_tools
    from settings import Settings
except:
    # Test run
    import os
    os.sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../..')
    import file_tools, clean
    from settings import Settings

class Mesh:


    # Initialization
    def __init__(self, INP_file=None, INP_code=None, old=None):
        self.nodes = {} # all mesh nodes with coordinates
        self.nsets = {} # node sets
        self.elements = {} # all mesh elements composition
        self.elsets = {} # element sets
        self.surfaces = {} # with corresponding nodes and element faces

        # Mesh bounds to avoid camera flying to infinity
        self.bounds = [1e+6,-1e+6]*3 # Xmin,Xmax, Ymin,Ymax, Zmin,Zmax

        # Mesh being reparsed
        self.old = old
        if not old:
            self.old = self

        # Get lines from INP source
        if INP_file and not INP_code:
            # Open and read whole the .inp-file
            lines = file_tools.readLines(INP_file, include=True)
        elif INP_code and not INP_file:
            # Parse some piece of INP code
            lines = INP_code
        else:
            logging.warning('Nothing to parse!')
            return

        # Call parse methods for everything
        for attrName, attrValue in self.__dict__.items():
            if type(attrValue) == dict:
                try:
                    getattr(self, 'parse_' + attrName)(lines)
                    msg_text = '{} {} '.format(len(attrValue), attrName)
                    # msg_text += str([v.name for v in attrValue.values()])
                    # for k,v in attrValue.items():
                    #     msg_text += '<br/>\n{0}: {1}'.format(k, v)
                    logging.info(msg_text)
                except:
                    logging.error('Can\'t parse {}'.format(attrName))


    # Parse nodes with coordinates - *NODE keyword
    def parse_nodes(self, lines):
        for i in range(len(lines)):

            # Distinguish 'NODE' and 'NODE PRINT'
            if ',' in lines[i]:
                keyword_name = lines[i].split(',')[0]
            else:
                keyword_name = lines[i]

            if keyword_name.upper() == '*NODE':
                nodes = []
                lead_line = lines[i]
                match = re.search('NSET\s*=\s*([\w\-]*)', lead_line.upper())

                while i+1<len(lines) and not lines[i+1].startswith('*'): # read the whole block and return
                    a = lines[i+1].replace(',', ' ').split() # to avoid redundant commas in the end of line
                    num = int(a[0]) # node number
                    coords = [float(coord) for coord in a[1:]] # node coordinates
                    if len(coords) == 2: # in 2D case add Z coord equal to zero
                        coords.append(0)

                    # Create NODE
                    node = NODE(num, coords)

                    # Check duplicates
                    if num in self.nodes:
                        msg_text = 'Duplicated node {}.'.format(num)
                        logging.warning(msg_text)
                        del node
                    else:
                        if len(coords):
                            nodes.append(node)
                            self.nodes[num] = node

                            # Bounding box
                            for j,coord in enumerate(coords):
                                if coord < self.bounds[j*2]:
                                    self.bounds[j*2] = coord # update min coords values
                                if coord > self.bounds[j*2+1]:
                                    self.bounds[j*2+1] = coord # update max coords values
                        else:
                            msg_text = 'Node {} has no coordinates and will be removed.'.format(num)
                            logging.warning(msg_text)
                            del node

                    i += 1

                # If all nodes are named as a set
                if match:
                    name = lead_line[match.start(1):match.end(1)]
                    create_or_extend_set(self.nsets, name, nodes, NSET)

                # do not return to parse few *NODE sections


    # Parse node sets - *NSET keyword
    def parse_nsets(self, lines):
        for i in range(len(lines)):
            match = re.search('(\*NSET)\s*,.*NSET\s*=\s*([\w\-]*)', lines[i].upper())
            if match:
                name = lines[i][match.start(2):match.end(2)] # node set name
                nodes = []

                if not 'GENERATE' in lines[i].upper():
                    while i+1<len(lines) and not lines[i+1].startswith('*'):
                        a = lines[i+1].replace(',', ' ').split()
                        for n in a:
                            try:
                                # Single node number
                                node = self.old.nodes[int(n)]
                                nodes.append(node)
                            except ValueError:
                                # Node set name
                                nodes.extend(self.old.nsets[n].items)
                            except KeyError:
                                msg_text = 'NSET {} - there is no node {} in the mesh.'.format(name, n)
                                logging.warning(msg_text)
                        i += 1
                else:
                    try:
                        start, stop, step = re.split(',\s*', lines[i+1])
                    except:
                        start, stop = re.split(',\s*', lines[i+1])
                        step = 1
                    for n in list(range(int(start), int(stop)+1, int(step))):
                        try:
                            node = self.old.nodes[n]
                            nodes.append(node)
                        except KeyError:
                            msg_text = 'NSET {} - there is no node {} in the mesh.'.format(name, n)
                            logging.warning(msg_text)

                create_or_extend_set(self.nsets, name, nodes, NSET)
                # do not return to parse few *NSET sections


    # Parse elements composition - *ELEMENT keyword
    def parse_elements(self, lines):
        for i in range(len(lines)):
            if lines[i].upper().startswith('*ELEMENT'):
                lead_line = lines[i]
                match = re.search('TYPE\s*=\s*(\w*)', lead_line.upper())
                etype = lead_line[match.start(1):match.end(1)] # element type
                amount = self.amount_of_nodes(etype)
                elements = []
                match = re.search('ELSET\s*=\s*([\w\-]*)', lead_line.upper()) # if all elements are united in a set

                while i+1<len(lines) and not lines[i+1].startswith('*'): # there will be no comments

                    # Element nodes could be splitted into few lines
                    a = lines[i+1].replace(',', ' ').split()
                    while len(a) < amount + 1: # +1 for element number
                        a.extend( lines[i+2].replace(',', ' ').split() )
                        i += 1

                    num = int(a[0]) # element number

                    nodes = []
                    create_element = True
                    for n in a[1:]: # iterate over element's node numbers
                        if int(n) == 0: # it is possible in network element, type=D
                            n = int(a[2]) # take middle node to display in VTK
                        try:
                            node = self.old.nodes[int(n)]
                            nodes.append(node)
                        except KeyError:
                            msg_text = 'Element {} has no node {} and will be removed.'.format(num, n)
                            logging.warning(msg_text)
                            create_element = False

                    # Create ELEMENT
                    if create_element:
                        element = ELEMENT(num, etype, nodes)

                        # Check duplicates
                        if num in self.elements:
                            msg_text = 'Duplicated element {}.'.format(num)
                            logging.warning(msg_text)
                            del element
                        else:
                            elements.append(element)
                            self.elements[num] = element

                    i += 1

                # If all elements are named as a set
                if match:
                    name = lead_line[match.start(1):match.end(1)]
                    create_or_extend_set(self.elsets, name, elements, ELSET)

                # do not return to parse few *ELEMENT sections


    # Parse element sets - *ELSET keyword
    def parse_elsets(self, lines):
        for i in range(len(lines)):
            match = re.search('(\*ELSET)\s*,.*ELSET\s*=\s*([\w\-]*)', lines[i].upper())
            if match:
                name = lines[i][match.start(2):match.end(2)] # element set name
                elements = []

                if not 'GENERATE' in lines[i].upper():
                    while i+1<len(lines) and not lines[i+1].startswith('*'):
                        a = lines[i+1].replace(',', ' ').split()
                        for e in a:
                            try:
                                # Single element number
                                element = self.old.elements[int(e)]
                                elements.append(element)
                            except ValueError:
                                # Element set name
                                elements.extend(self.old.elsets[e].items)
                            except KeyError:
                                msg_text = 'ELSET {} - there is no element {} in the mesh.'.format(name, e)
                                logging.warning(msg_text)
                        i += 1
                else:
                    try:
                        start, stop, step = re.split(',\s*', lines[i+1])
                    except:
                        start, stop = re.split(',\s*', lines[i+1])
                        step = 1
                    for e in list(range(int(start), int(stop)+1, int(step))):
                        try:
                            element = self.old.elements[e]
                            elements.append(element)
                        except KeyError:
                            msg_text = 'ELSET {} - there is no element {} in the mesh.'.format(name, e)
                            logging.warning(msg_text)

                create_or_extend_set(self.elsets, name, elements, ELSET)

                # do not return to parse few *ELSET sections


    # Parse surfaces - *SURFACE keyword
    def parse_surfaces(self, lines):
        for i in range(len(lines)):
            skip = True

            # Surface name - required attribute
            name = ''
            match = re.search('\*SURFACE\s*,.*NAME\s*=\s*([\w\-]*)', lines[i].upper())
            if match:
                name = lines[i][match.start(1):match.end(1)]
                skip = False

            # Surface type - optional attribute
            stype = 'ELEMENT' # 'ELEMENT' or 'NODE'
            match = re.search('\*SURFACE\s*,.*TYPE\s*=\s*(\w*)', lines[i].upper())
            if match:
                stype = lines[i][match.start(1):match.end(1)]

            if not skip:
                if name + stype in self.surfaces:
                    msg_text = 'Duplicated surface name {}.'.format(name)
                    logging.warning(msg_text)
                items = []

                while i+1<len(lines) and not lines[i+1].startswith('*'):
                    _list = re.split(',\s*', lines[i+1])

                    if stype == 'ELEMENT':
                        """
                            TYPE=ELEMENT:
                            'surf3: [(1, S1), (2, S1), ...]'
                            'surf4: [(elset1, S2), (elset2, S2), ...]'
                        """

                        # Surface with element and face numbers
                        #   1, S1
                        #   2, S1
                        if re.match('^\d+,\s*S\d', lines[i+1]):
                            elem_num = int(_list[0])
                            surf_name = _list[1]
                            items.append((elem_num, surf_name))

                        # Surface with elset and face number
                        #   elset1, S1
                        #   elset2, S2
                        elif re.match('^[\w\-]+,\s*S\d', lines[i+1]):
                            elset_name = _list[0]
                            surf_name = _list[1]
                            for element in self.old.elsets[elset_name].items:
                                items.append((element.num, surf_name))

                    elif stype == 'NODE':
                        """
                            TYPE=NODE:
                            'surf1: [1, 2, 3, ...]'
                            'surf2: [nset1, nset2, ...]
                        """
                        for n in _list:
                            if len(n):
                                try:
                                    # Single node number
                                    node = self.old.nodes[int(n)]
                                    items.append(node)
                                except ValueError:
                                    # Node set name
                                    items.extend(self.old.nsets[n].items)

                    i += 1

                # Create new SURFACE and append to list
                self.surfaces[name + stype] = SURFACE(name, items, stype)


    # Get amount of nodes by CalculiX element type
    def amount_of_nodes(self, etype):
        try:
            return {
                   'C3D8': 8,
                   'F3D8': 8,
                  'C3D8R': 8,
                  'C3D8I': 8,
                   'C3D6': 6,
                   'F3D6': 6,
                   'C3D4': 4,
                   'F3D4': 4,
                  'C3D20': 20,
                 'C3D20R': 20,
                  'C3D15': 15,
                  'C3D10': 10,
                 'C3D10T': 10,
                     'S3': 3,
                   'M3D3': 3,
                   'CPS3': 3,
                   'CPE3': 3,
                   'CAX3': 3,
                     'S6': 6,
                   'M3D6': 6,
                   'CPS6': 6,
                   'CPE6': 6,
                   'CAX6': 6,
                     'S4': 4,
                    'S4R': 4,
                   'M3D4': 4,
                  'M3D4R': 4,
                   'CPS4': 4,
                  'CPS4R': 4,
                   'CPE4': 4,
                  'CPE4R': 4,
                   'CAX4': 4,
                  'CAX4R': 4,
                     'S8': 8,
                    'S8R': 8,
                   'M3D8': 8,
                  'M3D8R': 8,
                   'CPS8': 8,
                  'CPS8R': 8,
                   'CPE8': 8,
                  'CPE8R': 8,
                   'CAX8': 8,
                  'CAX8R': 8,
                    'B21': 2,
                    'B31': 2,
                   'B31R': 2,
                   'T2D2': 2,
                   'T3D2': 2,
                 'GAPUNI': 2,
               'DASHPOTA': 2,
                'SPRING2': 2,
                'SPRINGA': 2,
                    'B32': 3,
                   'B32R': 3,
                   'T3D3': 3,
                      'D': 3,
                'SPRING1': 1,
                'DCOUP3D': 1,
                   'MASS': 1,
            } [etype]
        except:
            return 2 # minimum possible


    # Replace current mesh attributes with reparsed mesh ones
    def updateWith(self, reparsedMesh):
        for attrName, attrValue in reparsedMesh.__dict__.items():
            if type(attrValue) == dict and len(attrValue):
                # print('Another mesh:', attrName, attrValue)
                for _setName, _setValue in attrValue.items():
                    # print('Nodes:', _setValue.items)
                    getattr(self, attrName)[_setName] = _setValue


    # Parse INP_code and update current Mesh
    def reparse(self, INP_code):
        pass


# Before modification checks if sets have set with the same name
def create_or_extend_set(sets, name, items, klass):
    if name in sets: # check duplicates
        sets[name].items.extend(items) # append to existing set
        logging.warning('Duplicated set name {}!'.format(name))
    else:
        sets[name] = klass(name, items) # create new set


class NODE:
    """
        1: [ 0.0, -1742.5, 0.0],
        2: [74.8, -1663.7, 0.0],
        ...
    """
    def __init__(self, num, coords):
        self.num = num
        self.name = str(num)
        self.coords = coords


class NSET:
    """
        'nset1': [1, 2, 3, 4],
        'nset2': [5, 6, 7, 8],
        ...
    """
    def __init__(self, name, nodes):
        self.name = name
        self.items = nodes


class ELEMENT:
    """
        1: [1, 2],
        2: [3, 4],
        ...
        11: [21, 22, 23],
        12: [24, 25, 26],
        ...
    """
    def __init__(self, num, etype, nodes):
        self.num = num
        self.name = str(num)
        self.type = etype
        self.nodes = nodes

        # Calculate centroid
        x = sum([node.coords[0] for node in self.nodes]) / len(nodes)
        y = sum([node.coords[1] for node in self.nodes]) / len(nodes)
        z = sum([node.coords[2] for node in self.nodes]) / len(nodes)
        self.centroid = [x, y, z] # coordinates of element's center


class ELSET:
    """
        'elset1': [1, 2, 3, 4],
        'elset2': [5, 6, 7, 8],
        ...
    """
    def __init__(self, name, elements):
        self.name = name
        self.items = elements


class SURFACE:
    """
        TYPE=NODE:
        'surf1: [1, 2, 3, ...]'
        'surf2: [nset1, nset2, ...]

        TYPE=ELEMENT:
        'surf3: [(1, S1), (2, S1), ...]'
        'surf4: [(elset1, S2), (elset2, S2), ...]'
    """
    def __init__(self, name, items, stype=None):
        self.name = name
        self.items = items
        if stype:
            self.type = stype
        else:
            self.type = 'ELEMENT'


# Test
if __name__ == '__main__':
    logging.info = print
    INP_file = os.path.dirname(os.path.abspath(__file__)) \
                    + '../../../../examples/default.inp'
    Mesh(INP_file=INP_file)

    # Recursively clean cached files in all subfolders
    clean.cache()