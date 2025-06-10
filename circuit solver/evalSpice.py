import numpy as np
import os

def evalSpice(filename):   
    p = []  # parts
    # Check if the file exists
    if not os.path.isfile(filename):
        raise FileNotFoundError("Please give the name of a valid SPICE file as input")  
    
    with open(filename, "r") as file:
        #reading the contents of file
        lines = file.readlines()       
        # to check whether we are in the circuit
        in_circuit = False
        # to check whether we find .circuit line
        found_circuit = False

        for line in lines:
            # checking for .circuit line
            if line.startswith(".circuit"): 
                #updating the flags
                in_circuit = True
                found_circuit = True
                continue # ignoring the .circuit line
            
            # checking for .end line
            if in_circuit and line.rstrip().endswith(".end"):
                in_circuit = False
                break
            
            if in_circuit:
                line = line.split('#', 1)[0].strip()  # Strip comments
               
                if line:
                    p_list = line.split()
                    if 'dc' in p_list:
                        # Remove 'dc' from the voltage source
                        p_list.remove('dc')  
                    
                    if len(p_list) >= 4:
                        # c,d as node1 and node2
                        part = {
                            'type': p_list[0][0],  # V for voltage, I for current, R for resistor
                            'c': p_list[1],
                            'd': p_list[2],
                            'value': p_list[3]
                        }
                        x=part['type']
                        # raise error if any element other than V,I,R is found
                        if x not in ['V', 'I', 'R']:
                            raise ValueError("Only V, I, R elements are permitted")                       
                        # adding the data into a list
                        p.append(part)
    
    s = []
    for i in lines:
        x = i.split()  # Split the line by spaces
        if x and x[0][0] == 'V':  # Ensure the line isn't empty and the first component starts with 'V'
            s.append(x[0])  # Append the voltage source name to the list

        # raise error if .circuit is not found
        if not found_circuit:
            raise ValueError("Malformed circuit file")
        # raise error if only 1 kind of elments are present
        types = set( part['type'] for part in p)
        if len(types) == 1:
            raise ValueError("Circuit error: no solution")
    
    Z, Y, nodes, V = create_matrices(p)
    # solving the matrix
    sol = np.linalg.solve(Z, Y)
    voltages = sol[:len(nodes)]
    currents = sol[len(nodes):]
    # defining a dictionary to store nodes and node voltages
    V_dict = {"GND": 0.0}
    # node as key and node voltage as value
    for node, voltage in zip(nodes, voltages):
        V_dict[f"{node}"] = voltage 
    
    # defining a dictionary to store currents and voltage sources
    current_dict = {}
    for x, current in enumerate(currents):
        voltage_source = V[x]
        current_dict[s[x]] = current        
    return V_dict, current_dict


def create_matrices(parts):
    R = []  # Resistors
    V = []  # Voltage sources
    I = []  # Current sources
    nodes = set()  # Set of nodes  
    for part in parts:
        # add the node into nodes set if it is not ground
        if part['c'] != 'GND':
            nodes.add(part['c'])
        if part['d'] != 'GND':
            nodes.add(part['d'])
        
        # adding the elments into their corresponding lists
        if part['type'] == 'R':
            R.append(part)
        elif part['type'] == 'V':
            V.append(part)
        elif part['type'] == 'I':
            I.append(part)
    
    # converting nodes set into a list
    nodes = list(nodes)
    # declaring Z and Y matrices with corresponding sizes
    Z = [[0 for _ in range(len(nodes) + len(V))] for _ in range(len(nodes) + len(V))]
    Y = [0 for _ in range(len(nodes) + len(V))]  
    #node mapping
    node_ = {node: x for x, node in enumerate(nodes)}

    for r in R:
        #checking whether the node is ground or not make it as none if it is ground
        if r['c'] != 'GND':
            c = node_[r['c']]
        else:
            c = None
        if r['d'] != 'GND':
            d = node_[r['d']]
        else:
            d = None   
        
        resistance = float(r['value'])
        conductance = 1 / resistance   
        # add conductance of indices of the matrix Z is same else subtract
        if c is not None:
            Z[c][c] += conductance
        if d is not None:
            Z[d][d] += conductance
        if c is not None and d is not None:
            Z[c][d] -= conductance
            Z[d][c] -= conductance
    
    for i in I:
        #checking whether the node is ground or not make it as none if it is ground
        if i['c'] != 'GND':
            c = node_[i['c']]
        else:
            c = None
        if i['d'] != 'GND':
            d = node_[i['d']]
        else:
            d = None
        
        I_value = float(i['value']) 
        # add current value for the first node and subtract it for second node      
        if c is not None:
            Y[c] -= I_value
        if d is not None:
            Y[d] += I_value
    
    for x, v in enumerate(V):
        #checking whether the node is ground or not make it as none if it is ground
        if v['c'] != 'GND':
            c = node_[v['c']]
        else:
            c = None
        if v['d'] != 'GND':
            d = node_[v['d']]
        else:
            d = None       
        
        V_value = float(v['value'])       
        # index for voltages
        V_row = len(nodes) + x       
        # make the value as 1 for 1st node and -1 for 2nd node
        if c is not None:
            Z[c][V_row] = 1
            Z[V_row][c] = 1
        if d is not None:
            Z[d][V_row] = -1
            Z[V_row][d] = -1       
        Y[V_row] = V_value            
    return Z, Y, nodes, V
