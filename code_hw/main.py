from connect.connect import connect
from src.drivers.sim_movement import RobotMovement # O les teves funcions
import time

def main():
    clientID = connect(19999)
    if clientID == -1: return

    robot = RobotMovement(clientID)
    robot.connect_motors()
    
    print("Moure endavant 3 segons...")
    start_time = time.time()
    
    while time.time() - start_time < 10.0:
        robot.up()
        
    robot.stop()
    print("Aturat.")

if __name__ == "__main__":
    main()