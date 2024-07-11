# objects.py
# Objects used by the project to carry the data used both for defining the design and 
#  writing the prompts and chemical manager files

from typing import List
from typing import Dict

import clr
clr.AddReference("LSAPI")
import LS_API

import utils
import chemical_manager_file
import prompts_file

class LSLibrary:
    name: str
    rows: int
    cols: int
    substrate_type: str
    substrate_position: str
    initial_cover_state: str
    
    def __init__(self, name: str, rows: int, cols: int, substrate_type: str, substrate_position: str, initial_cover_state: str):
        self.name = name
        self.rows = rows
        self.cols = cols
        self.substrate_type = substrate_type
        self.substrate_position = substrate_position
        self.initial_cover_state = initial_cover_state
        
class LSChemical:
    name: str
    substrate_type: str
    substrate_position: str
    dispense_mode: str
    
    def __init__(self, name: str, substrate_type: str, substrate_position: str, dispense_mode: str):
        self.name = name
        self.substrate_type = substrate_type
        self.substrate_position = substrate_position
        self.dispense_mode = dispense_mode
