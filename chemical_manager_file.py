# chemical_manager_file.py
# Implements a generator for the prompts input file required by the AS10 API

def ChemPart1(chemicals_part: str, libraries_part: str, dispense_modes_part: str) -> str:
    data: str
    with open(r'chempart1.xml', 'r') as file:
        data = file.read()
    data = data.replace('<!-- Chemicals Part -->', chemicals_part)
    data = data.replace('<!-- Libraries Part -->', libraries_part)
    data = data.replace('<!-- Dispense modes part -->', dispense_modes_part)
    return data

def ChemPart2(name: str, substrate_type: str, substrate_position: str) -> str:
    data: str
    with open(r'chempart2.xml', 'r') as file:
        data = file.read()
    data = data.replace('<!-- Name -->', name)
    data = data.replace('<!-- SubstratePosition -->', substrate_type)
    data = data.replace('<!-- SubstrateType -->', substrate_position)
    return data

def ChemPart3(library_id: str, name: str, num_rows: str, num_cols: str, substrate_type: str, substrate_position: str) -> str:
    data: str
    with open(r'chempart3.xml', 'r') as file:
        data = file.read()
    data = data.replace('<!-- LibraryID -->', library_id)
    data = data.replace('<!-- Name -->', name)
    data = data.replace('<!-- NumOfRows -->', num_rows)
    data = data.replace('<!-- NumOfCols -->', num_cols)
    data = data.replace('<!-- SubstrateType -->', substrate_type)
    data = data.replace('<!-- SubstratePosition -->', substrate_position)
    return data
    
def ChemPart4(name: str, mode: str) -> str:
    data: str
    with open(r'chempart4.xml', 'r') as file:
        data = file.read()
    data = data.replace('%%Chemical Name%%', name)
    data = data.replace('%%Dispense Mode%%', mode)
    return data

class ChemicalManagerFile:
    chem_part_2: str
    chem_part_3: str
    chem_part_4: str
    
    def __init__(self):
        self.chem_part_2 = ''
        self.chem_part_3 = ''
        self.chem_part_4 = ''

    def AddChemical(self, name: str, substrate_position: str, substrate_type: str, dispense_mode) -> None:
        self.chem_part_2 += ChemPart2(name, substrate_position, substrate_type)
        self.chem_part_4 += ChemPart4(name, dispense_mode)

    def AddLibrary(self, library_id: str, name: str, num_rows: str, num_cols: str, substrate_type: str, substrate_position: str) -> None:
        self.chem_part_3 += ChemPart3(library_id, name, num_rows, num_cols, substrate_type, substrate_position)

    def Write(self, path: str):
        data = ChemPart1(self.chem_part_2, self.chem_part_3, self.chem_part_4)
        with open(path, 'w') as file:
            file.write(data)
