#!/usr/bin/python3

from subprocess import Popen, check_output
from signal import signal, SIGINT, SIGTERM
from usb.core import find, USBTimeoutError, USBError
import usb.util
import time


class NovaHeadset:
    VID = 0x1038
    PID = 0x2202
    INTERFACE = 0x5
    ENDPOINT_TX = 0x04
    ENDPOINT_RX = 0x86
    MSGLEN = 64
    TX = 0x06
    RX = 0x45
    CHATMIX_ENABLE = 0x49
    SONAR_ICON = 0x8d
    VOLUME = 0x37
    CHATMIX = 0x64
    EQ = 0x31
    EQ_PRESET = 0x2e
    FEATURE_STATUS = 0x47
    FEATURE_UNKNOWN1 = 0x36
    FEATURE_UNKNOWN2 = 0x21
    CHATMIX_CONTROLS_ENABLED = False
    SONAR_ICON_ENABLED = False
    CLOSE = False
    
    PW_ORIGINAL_SINK = None
    PW_GAME_SINK = "NovaGame"
    PW_CHAT_SINK = "NovaChat"
    PW_LOOPBACK_GAME_PROCESS = None
    PW_LOOPBACK_CHAT_PROCESS = None

    def __init__(self):
        self.dev = find(idVendor=self.VID, idProduct=self.PID)
        if self.dev is None:
            raise ValueError("Device not found")

        print(f"Found device: {self.dev}")

        for interface in [3, 4, 5]:
            try:
                if self.dev.is_kernel_driver_active(interface):
                    print(f"Detaching kernel driver from interface {interface}")
                    self.dev.detach_kernel_driver(interface)
            except USBError as e:
                print(f"Error detaching kernel driver from interface {interface}: {e}")

        try:
            print("Resetting device...")
            self.dev.reset()
            time.sleep(0.5)
        except USBError as e:
            print(f"Error resetting device: {e}")

        try:
            print("Setting configuration...")
            self.dev.set_configuration()
        except USBError as e:
            print(f"Error setting configuration: {e}")

        print("Finding endpoints...")
        cfg = self.dev.get_active_configuration()
        
        try:
            print(f"Claiming interface {self.INTERFACE}...")
            if self.dev.is_kernel_driver_active(self.INTERFACE):
                self.dev.detach_kernel_driver(self.INTERFACE)
            usb.util.claim_interface(self.dev, self.INTERFACE)
            
            intf = cfg[(self.INTERFACE,0)]
            ep = intf[0]
            if ep.bEndpointAddress == self.ENDPOINT_RX:
                self.ep_in = ep
                print(f"Successfully claimed interface {self.INTERFACE} with endpoint {ep.bEndpointAddress:02x}")
            else:
                raise ValueError(f"Unexpected endpoint: {ep.bEndpointAddress:02x}")
        except USBError as e:
            print(f"Error claiming interface: {e}")
            raise

        self.ep_out = None
        print(f"Using interface {self.INTERFACE} with IN endpoint {self.ep_in.bEndpointAddress:02x}")

    def _create_msgdata(self, command: int, feature: int, value: int) -> bytes:
        data = bytes([command, feature, value])
        return data.ljust(self.MSGLEN, b'\0')

    def _send_command(self, command: int, feature: int, value: int, retries=3):
        data = self._create_msgdata(command, feature, value)
        print(f"Sending command: {' '.join(f'{b:02x}' for b in data[:3])}")
        
        for attempt in range(retries):
            try:
                result = self.dev.ctrl_transfer(
                    bmRequestType=0x21,
                    bRequest=0x09,
                    wValue=0x0300,
                    wIndex=self.INTERFACE,
                    data_or_wLength=data,
                    timeout=1000
                )
                print(f"Sent {result} bytes")
                return True
            except USBTimeoutError:
                print(f"Timeout on attempt {attempt + 1}")
                if attempt < retries - 1:
                    time.sleep(0.1)
            except USBError as e:
                print(f"USB Error: {e}")
                if attempt < retries - 1:
                    time.sleep(0.1)
        return False

    def _query_chatmix(self):
        # Just send the chatmix query command
        return self._send_command(0x06, 0x64, 0)
        
    def set_chatmix_controls(self, state: bool):
        if self._send_command(self.TX, self.CHATMIX_ENABLE, int(state)):
            self.CHATMIX_CONTROLS_ENABLED = state

    def set_sonar_icon(self, state: bool):
        if self._send_command(self.TX, self.SONAR_ICON, int(state)):
            self.SONAR_ICON_ENABLED = state

    def _detect_original_sink(self):
        if self.PW_ORIGINAL_SINK:
            return
        try:
            sinks = check_output(["pw-cli", "ls", "Node"]).decode().split("\n")
            for sink in sinks:
                if "SteelSeries_Arctis_Nova" in sink and "Audio/Sink" in sink:
                    id = sink.split()[1]
                    self.PW_ORIGINAL_SINK = id
                    print(f"Found headset sink: {id}")
                    break
            
            if not self.PW_ORIGINAL_SINK:
                try:
                    sinks = check_output(["pactl", "list", "sinks", "short"]).decode().split("\n")
                    for sink in sinks:
                        if not sink:
                            continue
                        name = sink.split("\t")[1]
                        if "SteelSeries_Arctis_Nova" in name:
                            self.PW_ORIGINAL_SINK = name
                            print(f"Found headset sink: {name}")
                            break
                except:
                    print("Could not access PulseAudio, trying default sink...")
                    self.PW_ORIGINAL_SINK = "@DEFAULT_AUDIO_SINK@"
            
            if not self.PW_ORIGINAL_SINK:
                print("Warning: Could not find Nova headset, using default sink")
                self.PW_ORIGINAL_SINK = "@DEFAULT_AUDIO_SINK@"
                
        except Exception as e:
            print(f"Warning: Error detecting audio sink: {e}")
            print("Using default sink...")
            self.PW_ORIGINAL_SINK = "@DEFAULT_AUDIO_SINK@"

    def _start_virtual_sinks(self):
        try:
            self._detect_original_sink()
            cmd = [
                "pw-loopback",
                "-P",
                self.PW_ORIGINAL_SINK,
                "--capture-props=media.class=Audio/Sink",
                "-n",
            ]
            print("Creating virtual Game sink...")
            self.PW_LOOPBACK_GAME_PROCESS = Popen(cmd + [self.PW_GAME_SINK])
            time.sleep(0.5)
            
            print("Creating virtual Chat sink...")
            self.PW_LOOPBACK_CHAT_PROCESS = Popen(cmd + [self.PW_CHAT_SINK])
            time.sleep(0.5)
            
            print("Testing sink control...")
            test_cmd = ["pactl", "set-sink-volume", f"input.{self.PW_GAME_SINK}", "100%"]
            result = Popen(test_cmd)
            if result.wait() != 0:
                print("Warning: Could not control sink volume with pactl")
                print("Trying with pw-cli...")
                test_cmd = ["pw-cli", "set-param", f"input.{self.PW_GAME_SINK}", "Props", '{ "volume": 1.0 }']
                result = Popen(test_cmd)
                if result.wait() != 0:
                    raise Exception("Could not control sink volume")
        except Exception as e:
            print(f"Error setting up virtual sinks: {e}")
            self._remove_virtual_sinks()
            raise

    def _remove_virtual_sinks(self):
        if self.PW_LOOPBACK_GAME_PROCESS:
            self.PW_LOOPBACK_GAME_PROCESS.terminate()
        if self.PW_LOOPBACK_CHAT_PROCESS:
            self.PW_LOOPBACK_CHAT_PROCESS.terminate()

    def monitor_responses(self):
        print("Starting response monitoring...")
        last_query_time = 0
        last_value = None
        use_pwcli = False
        
        try:
            self._start_virtual_sinks()
            
            while not self.CLOSE:
                current_time = time.time()
                
                if current_time - last_query_time >= 0.1:
                    self._query_chatmix()
                    last_query_time = current_time
                
                try:
                    data = self.ep_in.read(self.MSGLEN, timeout=100)
                    if len(data) >= 3:
                        cmd = data[0]
                        feature = data[1]
                        value = data[2]
                        
                        # Only process ChatMix messages (feature 0x64)
                        if cmd == 0x45 and feature == 0x64:
                            print(f"\nChatMix Movement:")
                            print(f"Raw value: {value} (0x{value:02x})")
                            
                            # Direct mapping: 0x00 = full chat, 0x64 = full game
                            game_percent = int((value / 100.0) * 100)
                            chat_percent = 100 - game_percent
                            
                            if game_percent != last_value:
                                last_value = game_percent
                                print(f"ChatMix: {game_percent}% Game / {chat_percent}% Chat")
                                
                                try:
                                    if not use_pwcli:
                                        Popen(["pactl", "set-sink-volume", f"input.{self.PW_GAME_SINK}", f"{game_percent}%"])
                                        Popen(["pactl", "set-sink-volume", f"input.{self.PW_CHAT_SINK}", f"{chat_percent}%"])
                                    else:
                                        game_vol = game_percent / 100.0
                                        chat_vol = chat_percent / 100.0
                                        Popen(["pw-cli", "set-param", f"input.{self.PW_GAME_SINK}", "Props", f'{{ "volume": {game_vol} }}'])
                                        Popen(["pw-cli", "set-param", f"input.{self.PW_CHAT_SINK}", "Props", f'{{ "volume": {chat_vol} }}'])
                                except:
                                    if not use_pwcli:
                                        use_pwcli = True
                                        print("Switching to pw-cli for volume control...")
                                    else:
                                        print("Warning: Could not set volumes")
                                
                                bar_length = 40
                                game_bars = int((game_percent / 100) * bar_length)
                                chat_bars = bar_length - game_bars
                                print(f"[{'G' * game_bars}{'C' * chat_bars}]")
                        
                except USBTimeoutError:
                    continue
                except USBError as e:
                    print(f"USB Error while reading: {e}")
                    time.sleep(0.1)
        finally:
            self._remove_virtual_sinks()

    def close(self, signum=None, frame=None):
        print("Closing device...")
        self.CLOSE = True
        if self.CHATMIX_CONTROLS_ENABLED:
            self.set_chatmix_controls(False)
        if self.SONAR_ICON_ENABLED:
            self.set_sonar_icon(False)
        self._remove_virtual_sinks()
        usb.util.dispose_resources(self.dev)


if __name__ == "__main__":
    nova = NovaHeadset()
    signal(SIGINT, nova.close)
    signal(SIGTERM, nova.close)

    try:
        print("\nTrying to enable ChatMix controls...")
        nova.set_chatmix_controls(True)
        time.sleep(0.2)
        
        print("\nTrying to enable Sonar icon...")
        nova.set_sonar_icon(True)
        time.sleep(0.2)

        print("\nQuerying current ChatMix value...")
        nova._query_chatmix()
        time.sleep(0.2)

        print("\nStarting monitoring...")
        nova.monitor_responses()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        nova.close()