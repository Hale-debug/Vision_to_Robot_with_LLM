import numpy as np


# 直线轨迹插值
def linear_interpolation(start, end, steps=20):

    trajectory = []

    for i in range(steps + 1):

        t = i / steps

        point = (
            (1 - t) * np.array(start) +
            t * np.array(end)
        )

        trajectory.append(point.tolist())

    return trajectory