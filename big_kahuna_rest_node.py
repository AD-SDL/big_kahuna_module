"""
REST-based node that interfaces with WEI and provides various fake actions for testing purposes
"""

import time
from typing import Annotated
from zipfile import ZipFile
import as10
from fastapi import UploadFile
from fastapi.datastructures import State
from wei.modules.rest_module import RESTModule
from wei.types import StepFileResponse, StepResponse, StepStatus
from wei.types.module_types import (
    LocalFileModuleActionResult,
    Location,
    ModuleState,
    ValueModuleActionResult,
)
from wei.types.step_types import ActionRequest

# * Test predefined action functions


bk_rest_node = RESTModule(
    name="big_kahuna_node",
    description="A module for the big kahuna",
    version="1.0.0",
    resource_pools=[],
    model="big_kahuna",
    actions=[],
)



@bk_rest_node.startup()
def test_node_startup(state: State):
    """Initializes the module"""
    chem_temp_file_name = '6f39751ddd88503c934b.xml'
    prompts_temp_file_name = 'd2513e9392d40c23ce8a.xml'
    state.as_client = as10.FindOrStartAS()
    
    if as10.GetState(state.as_client) != "Stopped":
        raise(Exception("Robot not Idle!"))

@bk_rest_node.state_handler()
def state_handler(state: State) -> ModuleState:
    """Handles the state of the module"""
    module_status = as10.GetState(state.as_client)
    if module_status == "Stopped":
       state.status = "IDLE"
    elif module_status == "Running":
        state.status = "BUSY"
    else:
        module_status == "ERROR"

    return ModuleState(status=state.status, error=state.error)


@bk_rest_node.action()
def run_experiment(
    state: State,
    action: ActionRequest,
    design_id: Annotated[int, "The experiment design to run"],
    prompts_path: Annotated[str, "The prompts file to use"],
    chem_path: Annotated[str, "The chem file to use"],
    tip_manager_path: Annotated[str, "The chem file to use"] = None,

) -> StepResponse:
    """runs a pre-configured experiment"""
    # Write the temporary files (chemical manager and prompts)
    
    
    # Start the run via AS10 API
    as_client =state.as_client
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
        return StepStatus.step_succeeded()
    elif final_status == "Experiment aborted":
        print("The experiment was aborted")
        return StepStatus.step_failed()
    else:
        print("Unexpected final status: " + final_status)
        StepStatus.step_failed()
        
    # Clean up temporary files



if __name__ == "__main__":
    bk_rest_node.start()
