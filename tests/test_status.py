from huber_pilot_one import ThermostatStatus



def test_thermostat_status():
    status = ThermostatStatus(raw=1)
    assert(status.temp_control_active == True) 
    print(status)
