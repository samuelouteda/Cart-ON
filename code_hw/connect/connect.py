import connect.sim as sim

def connect(port):
# Establece la conexión a COPPELIA
# El port debe coincidir con el puerto de conexión en VREP  -- DALE AL PLAY !!!
# retorna el número de cliente o -1 si no puede establecer conexión
    sim.simxFinish(-1) # just in case, close all opened connections
    clientID=sim.simxStart('127.0.0.1',port,True,True,2000,5) # Conectarse
    if clientID == 0: print("Conectat a", port)
    else: print("No esta connectat")
    return clientID

def connect_dc_motors(clientID):
    _,DC_R=sim.simxGetObjectHandle(clientID,'DC_R',sim.simx_opmode_blocking)
    _,DC_L=sim.simxGetObjectHandle(clientID,'DC_L',sim.simx_opmode_blocking)
    print(f"Motor R: {DC_R}, Motor L: {DC_L}")
    return DC_L, DC_R
    