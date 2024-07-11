# prompts_file.py
# Implements a generator for the prompts input file required by the AS10 API

from typing import List

# Constants
not_covered_state = "None"
covered_state = "Covered"

def PromptsPart1(initial_library_states: str, initial_source_states: str) -> str:
    data: str
    with open(r'promptspart1.xml', 'r') as file:
        data = file.read()
    data = data.replace('<!-- Initial library states -->', initial_library_states)
    data = data.replace('<!-- Initial source states -->', initial_source_states)
    return data

def PromptsInitialState(identifier: str, state: str) -> str:
    return "[" + identifier + ":" + state + "]"

class PromptsFile:
    initial_library_states: List[str]
    initial_source_states: List[str]
    
    def __init__(self):
        self.initial_library_states = []
        self.initial_source_states = []

    def AddInitialLibraryState(self, library_id: str, initial_state: str) -> None:
        # initial_state may be "None" or "Covered" (not_covered_state or covered_state)
        self.initial_library_states.append(PromptsInitialState(library_id, initial_state))

    def AddInitialSourceState(self, substrate_position: str, initial_state: str) -> None:
        # initial_state may be "None" or "Covered"
        self.initial_source_states.append(PromptsInitialState(substrate_position, initial_state))

    def Write(self, path: str):
        data = PromptsPart1(';'.join(self.initial_library_states), ';'.join(self.initial_source_states))
        with open(path, 'w') as file:
            file.write(data)
