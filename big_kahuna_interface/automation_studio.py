import json
import os
import re
import shutil
import sys
import time
from datetime import datetime

import sila2.client


class AS10:  # v is verbosity
    def __init__(self, logs_dir: str, verbosity: bool):
        # statements
        self.stopped = "Stopped"
        self.aborted = "Aborted"
        self.running = "Running"
        self.paused = "Paused"
        self.pause_count = 0
        self.no_tips = "OutOfTips"
        self.active_prompt = "ActivePrompt"
        self.wait = "Timeout"
        self.error = "Error"

        self.verbose = verbosity
        self.do_record = (
            1  # to record status statements, 0 - none, 1 - to a file, 2 - also print
        )

        self.ID = 0  # ID of the library design
        self.clients = []  # cache for all discovered clients to close them
        self.client = None  # SILA client for AutomationClient
        self.start = None
        self.discovery = None  # error message in discovery
        self.es =  None   # Experiment Service, changed 7-25-2025
        self.ess =  None   # Experimental Status Service, changed 7-25-2025

        # state of the experiment, added 7-25-2025
        self.last_map = 0                   # last queried map
        self.map =  0                       # current LS map number
        self.total_maps = 0                 # total # of maps
        self.description = None             # map description
        self.current_action = None          # current action
        self.current_statement = None       # AS GUI rolling statement

        # quering
        self.timeout = 5  # sec between the calls
        self.response = None  # status query response
        self.status = None  # content of the status query
        self.state = None  # state from status
        self.next = None
        self.last = None
        self.was_aborted = (
            False  # whether the experiment was aborted before the completion
        )
        self.active = None  # active dialog status
        self.active_content = None  # cotent of the status
        self.info = None  # information in the active dialog
        self.title = None  # title of the active dialog
        self.option = None  # oprions in the active dialog
        # added 7-19-2025, checking time interval between the pauses
        self.signal_check = False             # test pause
        self.signal_code = 2000               # integer fixed code base (Send signal, wait for response => see CustomService codebook)
        self.signal_map = -1                  # map number before pause
        self.signal_accept = None             # criterion of acceptance, e.g. time interval between the pauses
        self.signal_last = None               # last code pause timestamp
        self.signal_current = None            # current code pause timestamp
        self.signal_dt = 0                    # last pause-to-pause interval
        self.signal_count = 0                 # signal count
        self.signal_long = 0                  # count of long pause-topause intervals
        self.signal_word = 31415              # code word in CurrentStatement to trigger signal action

        # logging
        self.logs_dir = logs_dir # AS logs folder
        self.logs = None  # all logs in the folder
        self.log = None  # the last log
        self.record = None  # file for status statements
        self.dir = ""  # promptsfile folder
        self.normal_response = json.loads(
            '{"Status":"Success","Content":"Experiment running","Error":"","StatusCode":0}'
        )
        self.normal_active = json.loads(
            '{"Status":"Success","Content":"No prompts are waiting for user input.","Error":"","StatusCode":1}'
        )
        self.problems = 0  # counter for "problematice" active dialogs

    def safe_record(self, s, divider=True):  # add to AS record
        if self.do_record == 2:
            print("\n>> record = %s\n" % s)
        if divider:
            s = "\n\n ************************  %s ************************\n\n" % s
        if self.record:
            try:
                self.record.write(s)
            except:
                print(">> No AS record file opened, record = %s" % s)

    def list_logs(self):
        return set(os.listdir(self.logs_dir))

    def get_log(self, state):
        if state == 0:
            self.logs = self.list_logs()
            self.log = None
        else:
            self.logs = self.list_logs() - self.logs
            for log in self.logs:
                if log.startswith("ASMain_") and log.endswith(".log"):
                    self.log = log
                    if self.verbose:
                        print("found log file %s" % log)

    def copy_log(self, folder):
        copy_from = os.path.join(self.logs_dir, self.log)
        copy_to = os.path.join(folder, self.log)
        shutil.copy2(copy_from, copy_to)
        

    def checkResult(self, response):
        response = json.loads(response)
        x = response["StatusCode"]
        if x < 0:
            print("ERROR (status code = %d): %s" % (x, response["Error"]))
            return 1
        return 0

    def discover(self, name):
        self.client = None
        attempt = 1
        while 1:
            try:
                self.client = sila2.client.SilaClient.discover(
                    server_name=name, insecure=True, timeout=self.timeout
                )

                if self.client not in self.clients:
                    self.clients.append(self.client)

                if self.verbose:
                    print(
                        "\nSILA client for server <%s> opened at %s, port = %d"
                        % (name, self.client.address, self.client.port)
                    )

                self.discovery = None
                return 0  # succeeded

            except Exception as e:
                self.discovery = f"Error: {e}"
                print(
                    "SILA client discovery exception for client <%s>:\n	 %s"
                    % (name, self.discovery)
                )

                if attempt == 5:  # makes 5 attempts to connect
                    return 1  # failed

                attempt += 1
                print("\n***** ATTEMPT %s TO CONNECT ******\n" % attempt)

    def StartAR(self):
        print("\n--- discover AutomationRemote\n")
        if self.discover("AutomationRemote"):
            return 1  # failed
        if self.client:
            self.start = self.client.AutomationStudioRemote.Start().ReturnValue
            return 0  # succeeded
        return 1  # failed

    def StartAS(self):
        print("\n--- discover AutomationStudio\n")
        if self.discover("AutomationStudio"):
            return 1  # failed
        if self.client:
            self.es = self.client.ExperimentService
            self.ess = self.client.ExperimentStatusService
            return 0  # succeeded
        else:
            return 1  # failed

    def FindOrStartAS(self):
        if self.StartAR():
            return 0  # failed
        if not self.checkResult(self.start):
            print(
                "--- Not getting the expected response after discovery of AutomationRemote, waiting 20 s"
            )
            time.sleep(20)  # changed from 20 s by UL
        if self.StartAS():
            return 0  # failed
        else:
            return 1  # succeeded

    def CloseAS(self):
        if self.verbose:
            print("\nstarting shutdown sequence")

        self.client.RunService.Abort()
        if self.verbose:
            print("Aborted RunService")

        self.client.AutomationStudio.Shutdown()
        if self.verbose:
            print("Shut down AutomationStudio")

        for client in self.clients:
            self.client.close()
            if self.verbose:
                print(
                    "Closed SILA client at %s, port %d" % (client.address, client.port)
                )

        time.sleep(5)  # needs to wait for the next SILA call to work

        if self.verbose:
            print("finished shutdown sequence\n")

    def RunAS(self, design_id, promptsfile, chemfile, tipfile):
        self.check = ""

        self.state = self.GetState()
        if self.state != self.stopped:
            print(">> AS not ready to run: state is not Stopped")
            print(" --- state = %s" % self.state)
            return 1

        if self.checkResult(self.es.ChooseDesignID(design_id).ReturnValue):
            self.check = "invalid design ID"
            print(self.check)
            return 1
        self.es.SetPrompts(promptsfile).ReturnValue
        if self.checkResult(self.es.SetPrompts(promptsfile).ReturnValue):
            self.check = "invalid promptsf file"
            print(self.check)
            return 1

        if self.checkResult(self.es.SetChemicalManager(chemfile).ReturnValue):
            self.check = "invalid chem maganger file"
            print(self.check)
            return 1

        if tipfile is not None:
            if self.checkResult(self.es.SetTipManagement(tipfile).ReturnValue):
                self.check = "invalid tips file"
                print(self.check)
                return 1

        if self.checkResult(self.client.RunService.Start().ReturnValue):
            self.check = "invalid runservice start call"
            print(self.check)
            return 1

        self.last = self.WaitNextState(self.stopped, 120)  # 2 min wait to start

        return 0

    def GetStatusContent(self):
        try: 
            self.response = json.loads(self.ess.GetStatus().ReturnValue)
            self.check_exp_status() # added 7-25-2025

            if self.response != self.normal_response and self.do_record:
                if self.verbose == 2: 
                    print(self.response) # added 7-22-2025 
                self.timestamp()
                self.safe_record("%s %s" % (self.stamp, self.response))

            return self.response['Content']
        except Exception as e:
            print("Status content error = %s" % e)
            return None
    def signal_action(self): # added 7-25-2025

            self.exp_status(0)
            self.signal_count +=1 
            self.signal_current = datetime.now()

            print("\n>> AS signal %d for map %d, received %s" % (self.signal_count, 
                                                                self.map, 
                                                                self.signal_current))

            if self.signal_last is not None:
                self.signal_dt = (self.signal_current - self.signal_last).total_seconds() / 60
                print(">> AS: Last signal pause time interval = %.2f min" % self.signal_dt)

            self.signal_last = self.signal_current

            if self.signal_check and self.signal_accept:
                if  self.signal_dt > self.signal_accept: # interval between signal pauses exceeds set duration
                    self.signal_long += 1
                    print("\n>> CAUTION: pause-to-pause step is taking too long")
                    message = "Expects %.1f min, step took %.1f min" % (self.signal_accept, self.signal_dt)
                    print(">> %s" % message)
                    if self.signal_long > 3:
                            print("\n>> WARNING: 3 last steps all took too long, alert sent")
                            #self.alert(subject="BK step takes too long 3 times", body=message, importance="High")
                            self.signal_accept = None
                else:
                    self.signal_long = 0 # null long interval counter

    def check_exp_status(self):
        if self.exp_status(0) > self.last_map: # added 7-25-2025
            self.last_map = self.map
            self.timestamp()
            self.safe_record("%s %s" % (self.stamp, self.current_statement))
            if str(self.signal_word) in self.current_statement:
                self.signal_action()

    def exp_status(self, opt=0):  # get the status of the AS experiment, print if opt=1
        self.map = 0
        self.total_maps = 0
        self.description = None

        r = json.loads(self.ess.GetExperimentStatus().ReturnValue)

        if r and 'Content' in r:
            c = r["Content"]

            if isinstance(c, dict) and "CurrentAction" in c:
                self.current_action = c.get("CurrentAction", "")
                self.current_statement = c.get("CurrentMap", "")

                if "Map" in self.current_statement:
                    match = re.match(r"Map (\d+) of (\d+):\s*(.+)", self.current_statement)
                    if match:
                        try:
                            self.map = int(match.group(1))
                            self.total_maps = int(match.group(2))
                            self.description = match.group(3)
                            if opt:
                                print(f"{self.current_action} :: {self.current_statement}")
                        except: pass

        return self.map

    def timestamp(self):
        now = datetime.now()
        self.stamp = now.strftime("%Y%m%d_%H%M%S")

    def GetActivePrompt(self):
        self.active = None
        self.active_content = None
        self.info = None
        self.title = None
        self.option = None

        self.active = json.loads(
            self.client.ExperimentStatusService.GetActivePrompt().ReturnValue
        )
        if self.active:
            if self.do_record and self.active != self.normal_active:
                self.timestamp()
                self.safe_record("ACTIVE = %s" % self.active)

            if self.active["StatusCode"] == 0:
                self.active_content = json.loads(self.active["Content"])

                if "InformationMessage" in self.active_content:
                    self.info = self.active_content["InformationMessage"]
                elif "value" in self.active_content:
                    self.info = self.active_content["value"]

                if "Title" in self.active_content:
                    self.title = self.active_content["Title"].lower()  # lower case

                if "Option" in self.active_content:
                    self.option = self.active_content["Option"]

    def GetState(self):
        self.status = self.GetStatusContent()

        if self.status == "Experiment running":
            self.GetActivePrompt()
            if self.active["StatusCode"] == 0:
                if self.info.startswith("No more tips"):
                    return self.no_tips
                else:
                    return self.active_prompt
            elif self.active["StatusCode"] == 1:
                return self.running

        elif self.status == "Experiment completed":
            return self.stopped

        elif self.status == "No experiment running":
            return self.stopped

        elif self.status == "Experiment paused":
            self.GetActivePrompt()
            return self.paused

        elif self.status == "Experiment aborted":
            return self.aborted

        elif self.status == "Experiment error":
            return self.error
        else:
            raise Exception("ERROR: Unexpected state, status = %s" % self.status)

    def WaitNextState(self, expected, dt):
        t = time.monotonic() + dt

        self.state = self.GetState()
        if self.state != expected:
            return self.state

        while time.monotonic() <= t:
            time.sleep(1)
            self.state = self.GetState()
            if self.state != expected:
                return self.state

        return self.wait

    def take_action(self, s):  # take action using options in prompt
        if s in self.option:
            self.client.ExperimentStatusService.SetInput(s)

    def run(
        self,
        design_ID,  # design ID
        promptsfile,  # prompts file w intial states
        chemfile=None,  # chem manager file, does not need to be supplied when Design Creator is used
        tipfile=None,  # tip file if used
        pause=False,  # stop and report text message when pause encountered
        resume=False,  # resume after pause
    ):
        self.problems = 0
        self.was_aborted = False
        self.dir = os.path.dirname(promptsfile)

        if resume:
            self.safe_record("BACK IN CONTRON", divider=True)
            if self.verbose:
                print(
                    "\n>> Run of design %d continues after Pause %d"
                    % (self.ID, self.pause_count)
                )

            self.client.ExperimentStatusService.SetInput("OK")
            self.last = self.GetState()

        else:
            self.record = None
            self.pause_count = 0
            self.ID = design_ID

            if chemfile:
                pass
            else:
                if "WithDC" not in promptsfile:
                    print(
                        "ERROR: Design Studio designs require promptsWithDC.xml input"
                    )
                    return "no-go"
                else:
                    self.dir = os.path.join(self.dir, str(self.ID))
                    if not os.path.exists(self.dir):
                        os.makedirs(self.dir)

            if self.do_record:
                self.timestamp()
                f = os.path.join(self.dir, "status_%s.log" % self.stamp)
                try:
                    self.record = open(f, "w")
                except:
                    print(">> Cannot open AS record file %s" % f)

            self.get_log(0)

            if self.verbose:
                print("\n>> Run of design %d started" % self.ID)
                print("AS prompt file = %s" % promptsfile)
                if tipfile:
                    print("Tip file = %s" % tipfile)
                if chemfile:
                    print("Chemical manager file = %s" % chemfile)
                else:
                    print("Design Creator design, no chemfile used")
                print("logs written to %s\n" % self.dir)

            if self.RunAS(design_ID, promptsfile, chemfile, tipfile):
                return "no-go"

            self.safe_record("STARTED", divider=True)

        while True:
            self.next = self.WaitNextState(self.last, 1)

            if self.next != self.wait:
                self.last = self.next

                if self.last == self.no_tips:
                    print("ERROR: The instrument is out of tips")
                    return "notips"

                elif self.last == self.active_prompt:
                    print(
                        "CAUTION: Active prompt state <%s> needs input: %s"
                        % (self.title, self.info)
                    )

                    if "paused" in self.title:
                        self.pause_count += 1
                        if self.verbose:
                            print("Pause %d, prompt=%s" % (self.pause_count, self.info))
                        if pause:
                            return self.info.split(".")[0]
                        else:
                            self.take_action("OK")

                    if "reset hardware" in self.title:
                        self.take_action("No")

                    if "experiment in progress" in self.title:
                        print("ERROR: Another experiment in progress")
                        sys.exit()

                elif self.last == self.paused:
                    print(
                        "CAUTION: Paused state <%s> needs input: %s"
                        % (self.title, self.info)
                    )

                    if "error" in self.info.lower():
                        self.problems += 1
                        if self.problems > 5:
                            self.take_action("Abort")
                        else:
                            self.take_action("Repeat Action")

                elif self.last == self.running:
                    print("ALERT: The experiment has resumed\n")
                    self.safe_record("RESUMED AFTER PROMPT")
                    self.problems = 0

                elif self.last == self.aborted:
                    print(
                        "ALERT: The experiment has been aborted, wait until it is completed\n"
                    )
                    self.was_aborted = True
                    time.sleep(30)  # 1 min to finish housekeeping
                    break

                elif self.last == self.stopped:
                    break

        self.get_log(1)

        if self.record:
            try:
                self.record.close()
            except:
                print(">> Cannot close AS record file")

        self.copy_log(self.dir)

        if not self.was_aborted:
            if self.verbose:
                print("FINAL: The experiment has completed")
            return "completed"
        else:
            if self.verbose:
                print("FINAL: The experiment was aborted")
            return "aborted"
