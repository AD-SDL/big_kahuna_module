# test.py
# Where the rubber meets the road: examples that use the LS and AS APIs to create and run designs that
#  are defined right here in this file using our own code

import time
import json
import tempfile
import os
from typing import List

import utils
import chemical_manager_file
import prompts_file
import as10
import ls10
import objects

# We will need to provide absolute paths to the AS10 API
sample_code_dir = os.getcwd()

# These are system configuration dependent,
#  Putting them here for reference
my_positions = [
'Deck 1-2 Position 3',
'Deck 3-4 Cool 1',
'Deck 3-4 Cool 2',
'Deck 3-4 Cool 3',
'Deck 9-10 Position 1',
'Deck 9-10 Position 2',
'Deck 9-10 Position 3',
'Deck 11-12 Heat-Stir 1',
'Deck 11-12 Heat-Stir 2',
'Deck 11-12 Heat-Stir 3']

# Names for temporary use (random as a principle to avoid conflict)
chem_temp_file_name = '6f39751ddd88503c934b.xml'
prompts_temp_file_name = 'd2513e9392d40c23ce8a.xml'

# Files included in the sample code
tips_full_path = sample_code_dir + '\\tips full.xml'
tips_empty_path = sample_code_dir + '\\tips empty.xml'


def start_run_and_wait(design_id: int, promptsfile: prompts_file.PromptsFile, chemfile: chemical_manager_file.ChemicalManagerFile, tip_manager_path: str = None) -> None:
    # Write the temporary files (chemical manager and prompts)
    prompts_path = tempfile.gettempdir() + "\\" + prompts_temp_file_name
    chem_path = tempfile.gettempdir() + "\\" + chem_temp_file_name
    promptsfile.Write(prompts_path)
    chemfile.Write(chem_path)
    
    # Start the run via AS10 API
    as_client = as10.FindOrStartAS()
    last_state = as10.RunAS(as_client, design_id, prompts_path, chem_path, tip_manager_path)
    
    print("Run started, waiting for completion")
    
    # Handle changes to the state of the instrument
    while True:
        next_state = as10.WaitNextState(as_client, last_state, 1)
        
        if next_state != as10.wait_timeout:
            # If "WaitNextState" did not timeout then the state has changed
            last_state = next_state
            
            if last_state == as10.no_tips_state:
                print("The instrument is out of tips and needs attention, please check the AS10 user interface")
            elif last_state == as10.active_prompt_state:
                # This client could now check what the prompt is and potentially handle it
                prompt_content = as10.GetActivePromptMessage(as10.GetActivePrompt(as_client))
                print("The AS10 user interface has displayed a prompt and needs attention: " + prompt_content)
            elif last_state == as10.paused_state:
                print("The user has paused the experiment")
            elif last_state == as10.running_state:
                print("The experiment has resumed")
            elif last_state == as10.stopped_state:
                break

    final_status = as10.GetStatusContent(as_client)
    if final_status == "Experiment completed":
        print("The experiment has completed")
    elif final_status == "Experiment aborted":
        print("The experiment was aborted")
    else:
        print("Unexpected final status: " + final_status)
        
    # Clean up temporary files
    os.remove(chem_path)
    os.remove(prompts_path)

def run1():
    # Define the library and chemicals
    #  (this sample is only set up for 1x1 reservoirs for chemicals)
    plate = objects.LSLibrary("Pancake1", 8, 12, "Plate 8x12 DWP", "Deck 9-10 Position 1", prompts_file.not_covered_state)
    chem1 = objects.LSChemical("syrup", "Plate 1x1 Reservoir", "Deck 1-2 Position 3", "High Visc Liquid|ADT")
    chem2 = objects.LSChemical("water", "Plate 1x1 Reservoir", "Deck 9-10 Position 2", "Low Visc Liquid|ADT")
    
    chemfile = chemical_manager_file.ChemicalManagerFile()
    promptsfile = prompts_file.PromptsFile()

    # Create the design via LS10 API
    design_units = "ul"
    ls10.CreateNewDesign("A design name", "No project", "No comment.")
    
    # Add the library
    ls10.AddLibrary(plate.name, plate.rows, plate.cols)
    
    # Add the chemicals
    ls10.AddChemical(chem1.name, design_units)
    chemfile.AddChemical(chem1.name, chem1.substrate_position, chem1.substrate_type, chem1.dispense_mode)
    promptsfile.AddInitialSourceState(chem1.substrate_position, prompts_file.not_covered_state)
    
    ls10.AddChemical(chem2.name, design_units)
    chemfile.AddChemical(chem2.name, chem2.substrate_position, chem2.substrate_type, chem2.dispense_mode)
    promptsfile.AddInitialSourceState(chem2.substrate_position, prompts_file.not_covered_state)
    
    # Add the dispense maps
    counter = 0
    counter += 1
    ls10.AddUniformMap(counter, chem2.name, plate.name, design_units, 9, "D1:G6", "50uLTip,6Tip")
    counter += 1
    ls10.AddUniformMap(counter, chem1.name, plate.name, design_units, 4, "E7:H12", "50uLTip,6Tip")
    counter += 1
    ls10.AddUniformMap(counter, chem2.name, plate.name, design_units, 3, "D1:H12", "50uLTip,6Tip")
    
    # Write to the DB and read out the library ID
    design_id = ls10.WriteToDb()
    written_libraries = ls10.GetLibraries()
    
    # The chemical manager and prompts files need to know what the library ID is for the plate
    #  This value is only known now that it was written to the DB
    library_id = written_libraries[0].ID
    chemfile.AddLibrary(str(library_id), plate.name, str(plate.rows), str(plate.cols), plate.substrate_type, plate.substrate_position)
    promptsfile.AddInitialLibraryState(str(library_id), plate.initial_cover_state)

    # Start the run via AS10 API
    print("Starting run with design ID " + str(design_id) + " and library ID(s) " + ", ".join(str(v.ID) for v in written_libraries))
    start_run_and_wait(design_id, promptsfile, chemfile)
    
def run2(tip_manager_path: str = None):
    # Define the library and chemicals
    #  (this sample is only set up for 1x1 reservoirs for chemicals)
    plate1 = objects.LSLibrary("Pancake1", 8, 12, "Plate 8x12 DWP", "Deck 9-10 Position 1", prompts_file.not_covered_state)
    plate2 = objects.LSLibrary("Pancake2", 8, 12, "Plate 8x12 DWP", "Deck 9-10 Position 2", prompts_file.not_covered_state)
    chem1 = objects.LSChemical("chocolate sauce", "Plate 1x1 Reservoir", "Deck 1-2 Position 3", "High Visc Liquid|ADT")
    chem2 = objects.LSChemical("boysenberry", "Plate 1x1 Reservoir", "Deck 9-10 Position 3", "High Visc Liquid|ADT")
    
    chemfile = chemical_manager_file.ChemicalManagerFile()
    promptsfile = prompts_file.PromptsFile()

    # Create the design via LS10 API
    design_units = "ul"
    ls10.CreateNewDesign("Breakfast", "", "")
    
    # Add the libraries
    libraries = [ plate1, plate2 ]  # in the same order that they are added to the design
    ls10.AddLibrary(plate1.name, plate1.rows, plate1.cols)
    ls10.AddLibrary(plate2.name, plate2.rows, plate2.cols)
    
    # Add the chemicals
    ls10.AddChemical(chem1.name, design_units)
    chemfile.AddChemical(chem1.name, chem1.substrate_position, chem1.substrate_type, chem1.dispense_mode)
    promptsfile.AddInitialSourceState(chem1.substrate_position, prompts_file.not_covered_state)
    
    ls10.AddChemical(chem2.name, design_units)
    chemfile.AddChemical(chem2.name, chem2.substrate_position, chem2.substrate_type, chem2.dispense_mode)
    promptsfile.AddInitialSourceState(chem2.substrate_position, prompts_file.not_covered_state)
    
    # Add the dispense maps
    counter = 0
    counter += 1
    ls10.AddUniformMap(counter, chem1.name, plate1.name, design_units, 5, "A1:B12", "50uLTip,6Tip")
    counter += 1
    ls10.AddUniformMap(counter, chem2.name, plate2.name, design_units, 5, "C1:D12", "50uLTip,6Tip")
    
    # Write to the DB and read out the library ID
    design_id = ls10.WriteToDb()
    written_libraries = ls10.GetLibraries()
    
    # The chemical manager and prompts files need to know what the library ID is for the plate
    #  This value is only known now that it was written to the DB
    for i in range(len(written_libraries)):
        library_id = written_libraries[i].ID
        chemfile.AddLibrary(str(library_id), libraries[i].name, str(libraries[i].rows), str(libraries[i].cols), libraries[i].substrate_type, libraries[i].substrate_position)
        promptsfile.AddInitialLibraryState(str(library_id), libraries[i].initial_cover_state)

    # Start the run via AS10 API
    print("Starting run with design ID " + str(design_id) + " and library ID(s) " + ", ".join(str(v.ID) for v in written_libraries))
    start_run_and_wait(design_id, promptsfile, chemfile, tip_manager_path)
    
def run3():
    # Execute run2 but with a full tip rack
    run2(tips_full_path)
    
def run4():
    # Execute run2 but with an empty tip rack
    run2(tips_empty_path)
    
def shutdown():
    as10.CloseAS()
