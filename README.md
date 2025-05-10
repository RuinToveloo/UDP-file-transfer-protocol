Instruction
    1. to activate network_emulator.sh, sender.sh and receiver.sh, please command:
        chmod +x ./network_emulator.sh
        chmod +x ./sender.sh
        chmod +x ./receiver.sh
    2. to run on network_emulator, the format for input is:
        python network_emulator.py 
            <emulator's receiving UDP port number in the forward direction>
            <receiver's network address>
            <receiver's receiving UDP port number>
            <emulator's receiving UDP port number in the backend direction>
            <sender's network address>
            <sender's receiving UDP port number>
            <maximum delay of the link in units of millisecond>
            <packet discard probability>
            <verbose-mode>
    3. to run on sender, the format for input is:
        python sender.py
            <host address of the network emulator>
            <UDP port number used by the emulator to emulator to receive data from the sender>
            <UDP port number used by the sender to receive ACKs from the emulator>
            <timeout interval in units of millisecond>
            <name of the file to be transferred>
    4. to run on receiver, the format for input is:
        python receiver.py
            <hostname for the network emulator>
            <UDP port number used by the emulator to receive ACKs from the receiver>
            <UDP port number used by the receiver to receive data from the emulator>
            <name of the file into which the received data is written>

