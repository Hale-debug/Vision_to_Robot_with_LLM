from kinematics import *

# 测试目标点
targets = [

    (160, 68, 10),

]

for xyz in targets:

    x,y,z = xyz

    print()
    print("================================")
    print("Target XYZ:")
    print(x,y,z)

    # IK
    angles = solve_ik(
        x,
        y,
        z
    )

    print()
    print("IK Angles:")
    print(angles)

    if angles is None:
        continue

    # FK
    x2,y2,z2 = forward_kinematics(
        angles[0],
        angles[1],
        angles[2]
    )

    print()
    print("FK XYZ:")
    print(
        round(x2,2),
        round(y2,2),
        round(z2,2)
    )

    # Error
    print()
    print("Error:")

    print(
        round(x2-x,2),
        round(y2-y,2),
        round(z2-z,2)
    )