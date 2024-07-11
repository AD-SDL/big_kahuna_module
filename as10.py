# as10.py
# A Python layer to wrap calls into the AS10 API (to keep other files uncluttered)

import sila2.client
from sila2.framework.errors.sila_connection_error import SilaConnectionError
import json
import time

import utils

# Constants
stopped_state = "Stopped"
running_state = "Running"
paused_state = "Paused"
no_tips_state = "OutOfTips"
active_prompt_state = "ActivePrompt"

wait_timeout = "Timeout"

def _checkResult(response_json: dict) -> None:
    if response_json['StatusCode'] < 0:
        raise Exception(response_json['Error'])
        
def StartAS() -> dict:
    sila_launcher = sila2.client.SilaClient.discover(server_name='AutomationRemote',insecure=True,timeout=utils.timeout_seconds)
    response = sila_launcher.AutomationStudioRemote.Start()
    return json.loads(response.ReturnValue)
    
def FindOrStartAS() -> sila2.client.SilaClient:
    # Attempt to start AS10. If already running, discover it. If it wasn't running, then discover with an extended timeout.
    start_response_json = StartAS()
    _checkResult(start_response_json)
    
    if start_response_json['StatusCode'] == 0:
        time.sleep(20)  # workaround for a possible bug where the AS10 Sila server will fail sometimes if discovery happens during startup
        return sila2.client.SilaClient.discover(server_name='AutomationStudio',insecure=True,timeout=utils.startup_timeout_seconds)
        
    return sila2.client.SilaClient.discover(server_name='AutomationStudio',insecure=True,timeout=utils.timeout_seconds)
    
def CloseAS() -> None:
    as_client = sila2.client.SilaClient.discover(server_name='AutomationStudio',insecure=True,timeout=utils.timeout_seconds)
    try:
        _checkResult(json.loads(as_client.AutomationStudio.Shutdown().ReturnValue))
    except SilaConnectionError:
        pass    # suppress this exception, there seems to be a bug somewhere so that Shutdown results in this exception
    
def RunAS(as_client: sila2.client.SilaClient, design_id: int, prompts_file_path: str, chemical_manager_path: str, tip_manager_path: str = None) -> str:
    if GetState(as_client) != stopped_state:
        raise Exception("The AS10 application is not ready to start an experiment")
        
    _checkResult(json.loads(as_client.ExperimentService.ChooseDesignID(design_id).ReturnValue))
    _checkResult(json.loads(as_client.ExperimentService.SetPrompts(prompts_file_path).ReturnValue))
    _checkResult(json.loads(as_client.ExperimentService.SetChemicalManager(chemical_manager_path).ReturnValue))
    if tip_manager_path is not None:
        _checkResult(json.loads(as_client.ExperimentService.SetTipManagement(tip_manager_path).ReturnValue))
    
    _checkResult(json.loads(as_client.RunService.Start().ReturnValue))
        
    return WaitNextState(as_client, stopped_state, 120)  # wait up to two minutes for the state to become other than stopped before returning
    
def GetStatusContent(as_client: sila2.client.SilaClient) -> str:
    status_response = json.loads(as_client.ExperimentStatusService.GetStatus().ReturnValue)
    return status_response['Content']
        
def GetState(as_client: sila2.client.SilaClient) -> str:
    status_response_content = GetStatusContent(as_client)
    if status_response_content == 'Experiment running':
        active_prompt_response = json.loads(as_client.ExperimentStatusService.GetActivePrompt().ReturnValue)
        if active_prompt_response['StatusCode'] == 0:
            active_prompt_content = json.loads(active_prompt_response['Content'])
            if 'InformationMessage' in active_prompt_content and active_prompt_content['InformationMessage'].startswith('No more tips'):
                return no_tips_state
            else:
                return active_prompt_state
        elif active_prompt_response['StatusCode'] == 1:
            return running_state
    elif status_response_content == 'Experiment completed':
        return stopped_state
    elif status_response_content == 'No experiment running':
        return stopped_state
    elif status_response_content == 'Experiment paused':
        return paused_state
    elif status_response_content == 'Experiment aborted':
        return stopped_state
    elif status_response_content == 'Experiment error':
        return stopped_state
    else:
        raise Exception("Unexpected state, status: " + status_response_content)
        
def WaitNextState(as_client: sila2.client.SilaClient, expected_state: str, timeout_sec: int) -> str:
    timeout_time = time.monotonic() + timeout_sec

    next_state = GetState(as_client)
    if next_state != expected_state:
        return next_state
    while time.monotonic() <= timeout_time:
        time.sleep(0.05)
        next_state = GetState(as_client)
        if next_state != expected_state:
            return next_state
    return wait_timeout

def GetActivePrompt(as_client: sila2.client.SilaClient) -> dict:
    active_prompt_response = json.loads(as_client.ExperimentStatusService.GetActivePrompt().ReturnValue)
    if active_prompt_response['StatusCode'] == 0:
        return json.loads(active_prompt_response['Content'])
    return None

def GetActivePromptMessage(parsed_json: dict) -> str:
    if 'InformationMessage' in parsed_json:
        return parsed_json['InformationMessage']
    elif 'value' in parsed_json:
        return parsed_json['value']
    
    raise Exception("Unexpected active prompt content format (I don't know what key to use to find the primary message)")
