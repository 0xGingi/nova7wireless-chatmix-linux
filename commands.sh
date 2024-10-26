#!/bin/bash

# Commands padded to 64 bytes with zeros
CHATMIX_ON="0649010100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
CHATMIX_OFF="0649010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
SONAR_ON="068d010100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
SONAR_OFF="068d010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

# Using hidraw5 which accepts our commands
HIDRAWDEV=/dev/hidraw5
sudo chmod 666 "$HIDRAWDEV"

# Function to send command and monitor
send_and_monitor() {
    local cmd=$1
    local desc=$2
    echo "Sending $desc..."
    printf "$cmd" | xxd -r -p - | tee "$HIDRAWDEV"
    sleep 2
    echo "Monitoring for 5 seconds..."
    timeout 5 usbhid-dump -s 3:4 -f -e stream
    echo "-------------------"
}

# Test sequence
send_and_monitor "$CHATMIX_ON" "ChatMix ON"
send_and_monitor "$CHATMIX_OFF" "ChatMix OFF"
send_and_monitor "$SONAR_ON" "Sonar ON"
send_and_monitor "$SONAR_OFF" "Sonar OFF"