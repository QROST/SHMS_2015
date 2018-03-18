# coding: utf-8

from matplotlib import pyplot as plt
from matplotlib import animation

import numpy as np

ta = list()
A1 = list()
A2 = list()
A3 = list()

t0_array = list()
t1_array = list()
t2_array = list()
t3_array = list()

v_array = list()
d_array = list()
f_array = list()

num_time = 0
num_vehicle = 0

l_m = 50
l_s = 50

fig = plt.figure()
ax = plt.axes(xlim=(-l_s, l_m + l_s), ylim=(-0.3, 0.3))

line_m_brg, = ax.plot([], [], lw=2)
line_l_brg, = ax.plot([-l_s, 0], [0, 0], lw=2)
line_r_brg, = ax.plot([l_m, l_m + l_s], [0, 0], lw=2)
arr_vehicle = list()  # [ax.annotate("", (0, 0),(0,0), arrowprops=dict(arrowstyle="->")) for i in range(20)]

num_x = 101
x = np.linspace(0, l_m, num_x)


def InitAnimate():
    global num_time, num_vehicle, arr_vehicle
    line_m_brg.set_data([], [])
    return line_m_brg, arr_vehicle


# play_animate function.  This is called sequentially
def UpdateAnimate(ii):
    global num_time, num_vehicle, arr_vehicle

    i = (2 * ii) % num_time  # 取值越大速度越大
    pi = np.pi
    pi1_l = pi / l_m
    pi2_l = pi * 2 / l_m
    pi3_l = pi * 3 / l_m

    mode1 = np.sin(pi1_l * x)
    mode2 = np.sin(pi2_l * x)
    mode3 = np.sin(pi3_l * x)

    t = ta[i]
    a1 = -A1[i]
    a2 = -A2[i]
    a3 = -A3[i]

    y = a1 * mode1 + a2 * mode2 + a3 * mode3  # y = A1*sin(1*pi*x/l) + A2*sin(2*pi*x/l) + A3*sin(3*pi*x/l) + ...

    line_m_brg.set_data(x, y)

    for idx_v in range(num_vehicle):
        t0 = t0_array[idx_v]
        #        t1 = t1_array[idx_v]
        #        t2 = t2_array[idx_v]
        t3 = t3_array[idx_v]

        v = v_array[idx_v]
        d = d_array[idx_v]
        f = f_array[idx_v]

        if t < t0 or t >= t3:
            arr_vehicle[idx_v].xy = (0, 0)  # arrow head
            arr_vehicle[idx_v].xyann = (0, 0)  # arrow tail
            continue

        if d == "from_left":
            x_pos = -l_s + (t - t0) * v
        else:
            x_pos = l_m + l_s - (t - t0) * v

        if 0 <= x_pos and x_pos < l_m:  # on main bridge
            ix = np.floor(x_pos / (l_m / (num_x - 1.0)))  # interpolent
            (x0, y0) = (x[ix], y[ix])
            (x1, y1) = (x[ix + 1], y[ix + 1])
            y_pos = ((x_pos - x0) * y1 - (x_pos - x1) * y0) / (x1 - x0)  # interpolent
        else:
            y_pos = 0  # y=0

        arr_vehicle[idx_v].xy = (x_pos, y_pos)  # arrow head
        arr_vehicle[idx_v].xyann = (x_pos, y_pos + 0.1)  # arrow tail

    return line_m_brg, arr_vehicle


# call the animator.  blit=True means only re-draw the parts that have changed.
def ShowAnimate():
    global num_time, num_vehicle, arr_vehicle
    f = open('output_analyst.txt', 'r')

    data_lines = f.readlines()
    num_time = len(data_lines) - 2

    for i in range(num_time):
        data_line = data_lines[i + 1]
        (t_, A1_, A2_, A3_) = eval(data_line)
        ta.append(t_)
        A1.append(A1_)
        A2.append(A2_)
        A3.append(A3_)

    f.close()

    f = open('output_monitor.txt', 'r')

    data_lines = f.readlines()
    num_vehicle = len(data_lines)

    arr_vehicle = [ax.annotate("", (0, 0), (0, 0), arrowprops=dict(arrowstyle="->")) for i in range(num_vehicle)]
    for i in range(num_vehicle):
        data_line = data_lines[i]
        (name, ts, delay, duration, force, velo, direction, brg_id) = eval(data_line)
        t0_array.append(ts)
        t1_array.append(ts + delay)
        t2_array.append(ts + delay + duration)
        t3_array.append(ts + delay + duration + delay)

        v_array.append(velo)
        d_array.append(direction)
        f_array.append(force)

    f.close()

    anim = animation.FuncAnimation(fig, UpdateAnimate, interval=5, init_func=InitAnimate, blit=False)

    plt.show()


ShowAnimate()
