from arm_controller import ArmController

arm = ArmController()

arm.connect()

while True:

    s1 = float(input("servo1: "))
    s2 = float(input("servo2: "))
    s3 = float(input("servo3: "))

    arm.send_angles(
        s1,
        s2,
        s3,
        75
    )