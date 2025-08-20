from sila2.client.sila_client import SilaClient
from sila2.discovery.listener import SilaServiceListener
from sila2.discovery.browser import SilaDiscoveryBrowser
import sila2
client = None
attempt = 1
client = sila2.client.SilaClient.discover(
        server_name="AutomationRemote", insecure=True, timeout=30
            )
print(client)
