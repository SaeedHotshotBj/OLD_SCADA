# ======================================
# PLC REGISTER MAP
# ======================================

# Main PLC data block
START_REGISTER = 100


# ======================================
# Production data registers
# Saved into PLC_Data table
# ======================================

B1 = 100
B2 = 101
B3 = 102
B4 = 103
B5 = 104
B6 = 105
B7 = 106
B8 = 107


G1 = 108
G2 = 109
G3 = 110
G4 = 111
G5 = 112
G6 = 113
G7 = 114
G8 = 115



# ======================================
# Trigger register
# Rising edge 0 -> 1 saves data
# ======================================

TRIGGER = 118



# ======================================
# Machine runtime registers
# ======================================

MILL_HOUR = 125

MIXER_HOUR = 128

PRESS_PELLET_HOUR = 131

# Trigger registers
MACHINE_RUNTIME_TRIGGER = 122

CURRENT = 135
VOLTAGE = 136



# ======================================
# Helper function
# Converts PLC address to Python list index
# ======================================

def register_to_index(register):

    return register - START_REGISTER