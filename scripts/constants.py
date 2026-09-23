# Author: Auto-generated
# Date: 2025-01-XX
# Description: Centralized constants for FORGE calculations.
#              Eliminates magic numbers throughout the codebase.

# Conversion constants
FEET_PER_MILE = 5280
SQUARE_FEET_PER_ACRE = 43560
HOURS_PER_YEAR = 8760

# Financial validation constants
MIN_DISCOUNT_RATE = -0.99  # Minimum allowed discount rate to prevent division by zero
TIMING_PATTERN_TOLERANCE = 0.001  # Tolerance for during_delay + during_construction == 1.0 (AFUDC-eligible patterns)

# Converter loss constants (as percentages, 0-1)
LCC_CONVERTER_LOSS = 0.0075  # 0.75% loss for Line Commutated Converters
VSC_CONVERTER_LOSS = 0.01    # 1.0% loss for Voltage Source Converters

# AC power factor constant
AC_POWER_FACTOR = 0.95  # Power factor for AC transmission phase current calculation

# Numerical tolerance constants
GROWTH_RATE_TOLERANCE = 1e-9  # Tolerance for checking if growth rate is effectively zero
DISCOUNT_GROWTH_EQUALITY_TOLERANCE = 1e-9  # Tolerance for checking if discount rate equals growth rate

# Transmission type constants
TRANSMISSION_TYPE_AC = "AC"
TRANSMISSION_TYPE_DC = "DC"

# Construction type constants
CONSTRUCTION_TYPE_OVERHEAD = "Overhead"
CONSTRUCTION_TYPE_UNDERGROUND = "Underground"
CONSTRUCTION_TYPE_UNDERGROUND_DIRECT_BURIED = "Underground direct-buried"
CONSTRUCTION_TYPE_UNDERGROUND_TUNNEL = "Underground tunnel"
CONSTRUCTION_TYPE_SUBSEA = "Subsea"

# Special value constants
CONVERTER_TYPE_NA = "NA"  # Used when AC (no converter)

