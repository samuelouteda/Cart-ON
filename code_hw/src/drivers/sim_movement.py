from connect import sim

class RobotMovement:
    def __init__(self, clientID):
        self.clientID = clientID
        self.left_motor = 0
        self.right_motor = 0
        self.speed = 2

    def connect_motors(self):
        _, self.left_motor = sim.simxGetObjectHandle(self.clientID, 'DC_L', sim.simx_opmode_blocking)
        _, self.right_motor = sim.simxGetObjectHandle(self.clientID, 'DC_R', sim.simx_opmode_blocking)
        print(self.right_motor, self.left_motor)

    def up(self):
        sim.simxSetJointTargetVelocity(self.clientID, self.right_motor,self.speed,sim.simx_opmode_streaming)
        sim.simxSetJointTargetVelocity(self.clientID, self.left_motor,self.speed,sim.simx_opmode_streaming)

    def down(self):
        sim.simxSetJointTargetVelocity(self.clientID, self.right_motor,self.speed,sim.simx_opmode_streaming)
        sim.simxSetJointTargetVelocity(self.clientID, self.left_motor,self.speed,sim.simx_opmode_streaming)

    def left(self):
        sim.simxSetJointTargetVelocity(self.clientID, 0,self.speed,sim.simx_opmode_streaming)
        sim.simxSetJointTargetVelocity(self.clientID, self.left_motor,self.speed,sim.simx_opmode_streaming)

    def right(self):
        sim.simxSetJointTargetVelocity(self.clientID, self.right_motor,self.speed,sim.simx_opmode_streaming)
        sim.simxSetJointTargetVelocity(self.clientID, self.left_motor,0,sim.simx_opmode_streaming)

    def stop(self):
        sim.simxSetJointTargetVelocity(self.clientID, self.right_motor,0,sim.simx_opmode_streaming)
        sim.simxSetJointTargetVelocity(self.clientID, self.left_motor,0,sim.simx_opmode_streaming)