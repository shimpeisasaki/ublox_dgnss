# Publication time, not a new GNSS measurement. Unknown fields must not be treated as zero-quality measurements.
std_msgs/Header header
uint8 UNKNOWN=0
uint8 NO_FIX=1
uint8 AUTONOMOUS=2
uint8 DIFFERENTIAL=3
uint8 RTK_FLOAT=4
uint8 RTK_FIXED=5
bool receiving
bool position_valid
bool solution_valid
uint8 solution
# solution is associated with status_itow; position quality with fix_itow.
uint32 status_itow
uint32 fix_itow
builtin_interfaces/Time status_stamp
builtin_interfaces/Time fix_stamp
bool differential_applied
float64[9] position_covariance
string reason
