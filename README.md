# Nova 7 Wireless Headset ChatMix Controller

A Python script to enable ChatMix functionality for SteelSeries Arctis Nova 7 Wireless on Linux, allowing you to control game and chat audio balance using the physical ChatMix dial.

## Features

- Enables ChatMix controls on the headset
- Creates virtual audio sinks for Game and Chat audio
- Real-time volume adjustment based on the ChatMix dial position
- Visual feedback of the current Game/Chat balance
- Support for both PulseAudio and PipeWire
- Only the first half of the dial is working, please help me finish this!

## Requirements

- Python 3.x
- pyusb library
- PulseAudio or PipeWire
- pw-loopback (part of PipeWire)
- pactl or pw-cli for volume control

## Installation

1. Install the required Python package:
   pip install pyusb

2. Create a udev rule to allow non-root access to the headset. Create a file `/etc/udev/rules.d/99-steelseries-nova.rules` with:
   ```SUBSYSTEM=="usb", ATTRS{idVendor}=="1038", ATTRS{idProduct}=="2202", MODE="0666"```

3. Reload udev rules:
```
sudo udevadm control --reload-rules
   
sudo udevadm trigger 
```

## Usage

1. Connect your Arctis Nova 7 Wireless headset

2. Run the script:
   python nova.py

3. Configure your applications:
   - Direct game and system audio to the "NovaGame" output
   - Direct chat applications (Discord, etc.) to the "NovaChat" output

4. Use the ChatMix dial on your headset to adjust the balance between game and chat audio

## How It Works

The script:
1. Detects and connects to the headset via USB
2. Creates two virtual audio sinks using PipeWire:
   - NovaGame: For game/system audio
   - NovaChat: For chat audio
3. Monitors the ChatMix dial position
4. Adjusts the volume of each sink based on the dial position:
   - Turning towards "GAME" increases game audio and decreases chat
   - Turning towards "CHAT" increases chat audio and decreases game

## Troubleshooting

- If you get permission errors, make sure the udev rule is properly set up
- If the virtual sinks aren't created, ensure PipeWire is running and pw-loopback is available
- If volume control doesn't work with pactl, the script will automatically try pw-cli

## Credits

- Thanks to https://github.com/Dymstro/nova-chatmix-linux for the initial implementation
