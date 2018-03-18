# coding: utf-8

import copy

import win32api
import pythoncom
import pyHook

import threading
import time

import numpy as np
from scipy.integrate import odeint
from matplotlib import pyplot as plt
from matplotlib import animation

import vehicle
import bridge

start_flag = False
finish_flag = False

sec_grade = 6  # 微秒

theBridge = bridge.Bridge("A_bridge")  # 运行桥梁
vehicle_dict = dict()  # 车辆字典

time_ref = 0  # 参考时间（初值零）

delay_min = vehicle.t_delay_fast  # 最小时间延迟
time_boundary = (0, 0)  # 时间边界（初值）

time_length = delay_min / 4.0  # 时间窗口长度（初值）
time_window = (0, 0)  # 时间窗口（初值）
num_seg_per_time_window = 50  # 每时窗分段数

A_pool = list()  # 模态坐标数据池
t_pool = list()  # 时间数据池
num_pool = 6  # 预留num_pool个数据池，供循环存放num_pool个时间窗口的模态响应数据
idx_pool = 0  # 当前数据池
idx_twin = 0  # 当前时间窗口序号

echo_flag_monitor = False
echo_flag_manager = False
echo_flag_schedul = False
echo_flag_analyst = False

file_monitor = None
file_manager = None
file_analyst = None
file_schedul = None
file_animate = None


def StrTimeInfo(caller=""):
    global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
    global sec_grade
    if caller == "Manager":
        if sec_grade == 3:  # 毫秒级
            fmt = "  time_window = (%6.3f, %6.3f)\n"
        else:  # 微秒级
            fmt = " time_window = (%9.6f, %9.6f)\n"
        return fmt % (time_window[0], time_window[1])

    if sec_grade == 3:  # 毫秒级
        fmt = "  time_cur = %6.3f,   time_window = (%6.3f, %6.3f),  time_boundary = (%6.3f, %6.3f)\n"
    else:  # 微秒级
        fmt = " time_cur = %9.6f,  time_window = (%9.6f, %9.6f), time_boundary = (%9.6f, %9.6f)\n"

    return fmt % (time_boundary[0], time_window[0], time_window[1], time_boundary[0], time_boundary[1])


class Monitor(threading.Thread):
    def __init__(self, cond, lock, name='Monitor'):
        threading.Thread.__init__(self)
        self.cond = cond
        self.name = name
        self.lock = lock

    def run(self):
        global file_monitor, echo_flag_monitor
        global start_flag, finish_flag

        file_monitor = open("output_monitor.txt", "w")
        if echo_flag_monitor:
            print "Monitor: key board hook OK."

        hm = pyHook.HookManager()  # 创建钩子管理对象
        hm.KeyDown = self.OnKeyBoardEvent  # 监听键盘事件

        hm.HookKeyboard()  # 设置键盘钩子
        pythoncom.PumpMessages()  # 进入循环

        if echo_flag_monitor:
            print "Monitor: exit."
        file_monitor.close()

        finish_flag = True

    def OnKeyBoardEvent(self, event):
        global vehicle_dict, theBridge
        global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
        global file_monitor, echo_flag_monitor
        global start_flag, finish_flag

        if start_flag == False:
            start_flag = True
            time_ref = round(time.time(), sec_grade)

        time_stamp = round(time.time() - time_ref, sec_grade)

        if event.KeyID == 81:  # Q
            vehicle_force = vehicle.MovingConcentrateForce(time_stamp, "from_left", "huge_slow", theBridge)
            vehicle_id = "HS_" + "%010.3f" % (time_stamp)
        elif event.KeyID == 65:  # A
            vehicle_force = vehicle.MovingConcentrateForce(time_stamp, "from_left", "small_fast", theBridge)
            vehicle_id = "SF_" + "%010.3f" % (time_stamp)
        elif event.KeyID == 80:  # P
            vehicle_force = vehicle.MovingConcentrateForce(time_stamp, "from_right", "huge_slow", theBridge)
            vehicle_id = "HS_" + "%010.3f" % (time_stamp)
        elif event.KeyID == 76:  # L
            vehicle_force = vehicle.MovingConcentrateForce(time_stamp, "from_right", "small_fast", theBridge)
            vehicle_id = "SF_" + "%010.3f" % (time_stamp)
        elif event.KeyID == 75:  # K
            self.lock.acquire()  # 加锁,避免冲突
            for i in range(200):
                vehicle_force = vehicle.MovingConcentrateForce(time_stamp, "from_left", "sequence2", theBridge, i)
                info = vehicle_force.Info()
                vehicle_id = info[0]
                vehicle_dict[vehicle_id] = vehicle_force  # 修改vehicle_dict
                file_monitor.write(str(vehicle_force.Info()) + "\n")
                if echo_flag_monitor:
                    print ", remain", vehicle_dict.keys()
                    print
            self.lock.release()  # 释放锁
        elif event.KeyID == 83:  # S
            self.lock.acquire()  # 加锁,避免冲突
            for i in range(200):
                vehicle_force = vehicle.MovingConcentrateForce(time_stamp, "from_left", "sequence", theBridge, i)
                info = vehicle_force.Info()
                vehicle_id = info[0]  # "SQ_" + "%02i" % (i)
                vehicle_dict[vehicle_id] = vehicle_force  # 修改vehicle_dict
                file_monitor.write(str(vehicle_force.Info()) + "\n")
                if echo_flag_monitor:
                    print ", remain", vehicle_dict.keys()
                    print
            self.lock.release()  # 释放锁
        elif event.KeyID == 90:  # Z
            print "Monitor: press key Z"
            win32api.PostQuitMessage()
            return True
        else:
            return True

        file_monitor.write(str(vehicle_force.Info()) + "\n")

        if echo_flag_monitor:
            print
            print "Monitor: time_stamp =", time_stamp,
            print ", new vehicle =", vehicle_force.Info(),

        self.lock.acquire()  # 加锁,避免冲突
        vehicle_dict[vehicle_id] = vehicle_force  # 修改vehicle_dict
        if echo_flag_monitor:
            print ", remain", vehicle_dict.keys()
            print
        self.lock.release()  # 释放锁

        return True


class Manager(threading.Thread):
    def __init__(self, cond, lock, name='Manager'):
        threading.Thread.__init__(self)
        self.cond = cond
        self.name = name
        self.lock = lock

    def SaveVehicleDict(self):
        for v_id in vehicle_dict.keys():  # 对荷载循环
            vehicle_force = vehicle_dict[v_id]
            fmt = "name =%s, stamp =%9.3f, delay =%9.3f, duration =%9.3f, force =%9.3f, velo =%9.3f, direction =%s, bridge_id =%s\n"
            file_manager.write(fmt % vehicle_force.Info())

    def run(self):
        global vehicle_dict, theBridge
        global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
        global echo_flag_manager, file_manager
        global sec_grade
        global start_flag, finish_flag

        file_manager = open("output_manager.txt", "w")

        while True:
            if start_flag == True: break  # 开始

        if echo_flag_manager:
            print "Manager: ready..., ",
            print StrTimeInfo()
            print

        while True:
            v_id_set = set()  # 空集合

            self.lock.acquire()  # 加锁
            for v_id in vehicle_dict.keys():  # 对荷载循环
                vehicle_force = vehicle_dict[v_id]
                if vehicle_force.LeaveBridgeCheck(time_window[0]):  # 检查是否离开桥梁
                    v_id_set.add(v_id)  # 放入已离桥车辆集合

            for v_id in v_id_set:
                TT = vehicle_dict[v_id].duration + vehicle_dict[v_id].delay
                if echo_flag_manager:
                    print "Manager: dele..., ", v_id, ", TT = ", TT,
                    print StrTimeInfo("Manager")
                    print
                    #                del vehicle_dict[v_id]                                  # 从字典中删除移动车辆荷载
            self.lock.release()  # 释放锁

            if finish_flag == True:
                self.SaveVehicleDict()
                break  # 结束

        file_manager.close()


class Schedul(threading.Thread):
    def __init__(self, cond, lock, name='Schedul'):
        threading.Thread.__init__(self)
        self.cond = cond
        self.name = name
        self.lock = lock

    def run(self):
        global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
        global echo_flag_schedul
        global file_schedul, start_flag

        file_schedul = open("output_schedul.txt", "w")

        while True:
            if start_flag == True:  break  # 开始

        delta_t = 0.1  # 积分求解的时间提前量，便于检验初始条件是否正确
        while True:
            time_cur = time.time() - time_ref
            if time_cur >= time_length - delta_t:   break  # 时间前进一个时间窗

        self.cond.acquire()

        time_front = time_length - delta_t + delay_min  # 时间前沿
        time_window = (time_front - time_length, time_front)  # 首时间窗
        time_boundary = (time_front - delay_min, time_front)  # 首时间边界
        idx_twin = 0  # 时间窗口序号
        idx_pool = idx_twin % num_pool

        while True:
            self.cond.notify()  # 发出通知
            if echo_flag_schedul:
                print "Schedul: wait...",
                print StrTimeInfo()
                print

            new_time_lower = time_window[1]  # 新时间窗下限
            new_time_upper = new_time_lower + time_length  # 新时间窗上限

            self.cond.wait()  # 等待通知
            file_schedul.write(StrTimeInfo())
            if echo_flag_schedul:
                print "Schedul: work...",
                print StrTimeInfo()

            while True:
                time_cur = round(time.time() - time_ref, sec_grade)  # 当前时间
                time_front = time_cur + delay_min  # 前沿时间
                time_boundary = (time_cur, time_front)

                if new_time_upper <= time_front:  # 时间窗口(time_lower, time_upper)必须介于(time_cur, time_front)之间，将时间窗口尽可能前移
                    time_window = (new_time_lower, new_time_upper)
                    idx_twin += 1
                    idx_pool = idx_twin % num_pool
                    break  # 跳出内层while

            if finish_flag == True:
                break

        file_schedul.close()

        self.cond.release()


class Analyst(threading.Thread):
    def __init__(self, cond, lock, name='Analyst'):
        threading.Thread.__init__(self)
        self.cond = cond
        self.lock = lock
        self.name = name
        self.v_dict = dict()

    def run(self):
        global vehicle_dict, theBridge
        global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
        global echo_flag_analyst, file_analyst
        global A_pool, t_pool, num_pool, idx_pool
        global start_flag, finish_flag

        file_analyst = open("output_analyst.txt", "w")  # 打开工作文档

        while True:
            if start_flag == True:  break  # 开始

        self.cond.acquire()  # condition启动

        num_mode = theBridge.num_mode
        t_num = num_seg_per_time_window

        y0 = [0.0] * (2 * num_mode)  # 分析开始时，零初始条件

        file_analyst.write(" time         A1                  A2                  A3\n")
        while True:
            if echo_flag_analyst: print "Analyst: wait..." + StrTimeInfo()

            self.cond.wait()  # 等待schedul的通知
            if echo_flag_analyst: print "Analyst: work..." + StrTimeInfo()

            analyst_t0 = time.time()

            self.lock.acquire()  # 加锁,避免分析时与manager冲突
            self.v_dict = copy.deepcopy(vehicle_dict)  # 深拷贝，避免引用式共享
            self.lock.release()  # 释放锁

            (t0, t1) = time_window  # 取时间窗的上下限
            t_array = np.linspace(t0, t1, t_num + 1)  # 离散时间数组

            analyst_t1 = time.time()

            y_array = odeint(self.dydt, y0, t_array)  # 调用odeint，求解各模态响应的时程曲线

            analyst_t2 = time.time()

            # 保存到数据池
            if echo_flag_analyst: print  "idx_twin =%6i,  idx_pool =%2i,  time_window =(%6.3f, %6.3f)\n" % (
                idx_twin, idx_pool, t0, t1)
            pos = idx_pool * t_num
            for i in range(t_num):
                t_pool[pos + i] = t_array[i + 1]
                A_pool[pos + i][:] = y_array[i + 1][0:(2 * num_mode):2]  # 仅取模态坐标，不取其导数

            for i in range(t_num):
                #                fmt = "     odeint:   idx_pool = %2i,    idx = %4i,   time = %6.3f,   A1 =%13.6e,   A2 = %13.6e,   A3 = %13.6e\n"
                #                file_analyst.write( fmt % (idx_pool, pos+i, t_array[i+1], y_array[i+1][0], y_array[i+1][2], y_array[i+1][4]))
                fmt = "%6.3f,      %13.6e,      %13.6e,      %13.6e\n"
                file_analyst.write(fmt % (t_array[i + 1], y_array[i + 1][0], y_array[i + 1][2], y_array[i + 1][4]))

            # fmt = "     t_pool A_pool:                            time = %6.3f,   A1 =%13.6e,   A2 = %13.6e,   A3 = %13.6e\n\n"
            #                file_analyst.write( fmt % (t_pool[pos+i], A_pool[pos+i][0], A_pool[pos+i][1], A_pool[pos+i][2]))

            idx_pool = (idx_pool + 1) % num_pool  # 指向下一个数据池，往复循环
            y0 = y_array[-1]  # 设置下一个时间窗的初始条件

            self.cond.notify()  # 通知schedul
            analyst_t3 = time.time()

            using_time = round(analyst_t2 - analyst_t1, 6)
            if echo_flag_analyst: print  "for time_window(%9.3f, %9.3f), odeint using time =%9.6f (sec)\n" % (
                t0, t1, using_time)
            using_time = round(analyst_t3 - analyst_t0, 6)
            if echo_flag_analyst: print  "                                       total  using time =%9.6f (sec)\n" % (
                using_time)
            if finish_flag == True:
                print "analyst finish."
                break

        file_analyst.close()

        self.cond.release()  # condition释放

    def dydt(self, y, t):  # 未知函数一阶导数dydt
        global theBridge

        omega = theBridge.omegaList
        zeta = theBridge.zetaList
        num_mode = theBridge.num_mode

        y_p = [0.0] * (num_mode * 2)

        m = theBridge.m
        l = theBridge.m_span  # 主跨长度
        pi_l = np.pi / l
        ml = m * l

        for i in range(num_mode):  # 对模态循环
            omg = omega[i]  # 取当前圆频率
            zt = zeta[i]  # 取当前阻尼比
            zt2 = zt + zt

            i2 = i + i
            y_p[i2] = y[i2 + 1]
            y_p[i2 + 1] = (-zt2 * y[i2 + 1] - omg * y[i2]) * omg

        for v_id in self.v_dict.keys():  # 对车辆字典循环
            mv = self.v_dict[v_id]  # 当前移动车辆

            f = mv.force  # 荷载
            v = mv.velocity  # 速度
            t0 = mv.time_stamp + mv.delay  # 上桥时刻

            f2_ml = (f + f) / ml  # 2*f/m/l
            T = mv.duration
            piv_l = pi_l * v

            for i in range(num_mode):  # 对模态循环
                i2p1 = i + i + 1
                if mv.OnBridgeCheck(t):  # 当前是否在桥上
                    if mv.direction == "from_left":  # 方向：从左向右
                        y_p[i2p1] = y_p[i2p1] + f2_ml * np.sin((i + 1.0) * piv_l * (t - t0))
                    else:  # 方向：从右向左
                        y_p[i2p1] = y_p[i2p1] + f2_ml * np.sin((i + 1.0) * piv_l * (T - (t - t0)))

        return y_p


fig = plt.figure()
ax = plt.axes(xlim=(-theBridge.s_span, theBridge.m_span + theBridge.s_span), ylim=(-0.3, 0.3))

line_m_brg, = ax.plot([], [], lw=2)  # 振动桥梁
line_l_brg, = ax.plot([-theBridge.s_span, 0], [0, 0], lw=2)
line_r_brg, = ax.plot([theBridge.m_span, theBridge.m_span + theBridge.s_span], [0, 0], lw=2)

arr_vehicle = [ax.annotate("", (0, 0), (0, 0), arrowprops=dict(arrowstyle="->")) for i in range(20)]  # 移动车辆


def InitAnimate():
    return line_m_brg, arr_vehicle


# play_animate function.  This is called sequentially
def UpdateAnimate(idx_f, num_mode, num_x, x, modeShapes, lock):
    global vehicle_dict, theBridge
    global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
    global A_pool, t_pool, num_pool, idx_pool, idx_twin
    global file_animate, echo_flag_animate
    global start_flag, finish_flag

    idx_t = (3 * idx_f) % (num_pool * num_seg_per_time_window)

    y = [0.0] * num_x

    t = t_pool[idx_t]
    A = A_pool[idx_t][:]

    file_animate.write("idx_f = %4i, idx_t =%4i,  time =%6.3f,   A1 =%13.6e,   A2 =%13.6e,   A3 =%13.6e\n" % (
        idx_f, idx_t, t, A[0], A[1], A[2]))

    for j in range(num_mode):
        y = y + A[j] * modeShapes[j]  # y = A1*sin(1*pi*x/l) + A2*sin(2*pi*x/l) + A3*sin(3*pi*x/l) + ...

    line_m_brg.set_data(x, y)

    lock.acquire()  # 加锁,避免分析时与manager冲突
    v_dict = copy.deepcopy(vehicle_dict)  # 深拷贝
    lock.release()  # 释放锁

    m_span = theBridge.m_span
    #    arr_vehicle = list()

    i_mv = 0
    for v_id in v_dict.keys():
        mv = v_dict[v_id]
        x_mv = mv.XPosition(t)

        xlim = ax.get_xlim()
        x_l = xlim[0]
        x_r = xlim[1]

        if x_l <= x_mv and x_mv <= x_r:  # 在 左引桥 + 主桥 + 右引桥 上
            if mv.OnBridgeCheck(t):  # 在主桥上
                itmp = np.floor(x_mv / (m_span / (num_x - 1.0)))  # 竖向位移 取 x_mv 坐标处的 挠度函数 插值
                (x0, y0) = (x[itmp], y[itmp])
                (x1, y1) = (x[itmp + 1], y[itmp + 1])
                y_mv = ((x_mv - x0) * y1 - (x_mv - x1) * y0) / (x1 - x0)  # 插值
            else:
                y_mv = 0  # 竖向位移取零

            # mv_arr = ax.annotate("", (0, 0),(0, 0), arrowprops=dict(arrowstyle="->"))  # 箭头表示移动车辆
            #            mv_arr.xy    = (x_mv, y_mv)                                                      # arrow head
            #            mv_arr.xyann = (x_mv, y_mv + 0.1)                                                # arrow tail

            #            arr_vehicle.append(mv_arr)

            arr_vehicle[i_mv].xy = (x_mv, y_mv)  # arrow head
            arr_vehicle[i_mv].xyann = (x_mv, y_mv + 0.1)  # arrow tail
        else:
            arr_vehicle[i_mv].xy = (101, 0)  # arrow head
            arr_vehicle[i_mv].xyann = (101, 0.1)  # arrow tail
        i_mv += 1

    if finish_flag == True:  file_animate.close()

    return line_m_brg, arr_vehicle


# call the animator.  blit=True means only re-draw the parts that have changed.
def ShowAnimate(lock):
    global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
    global file_animate, echo_flag_animate
    global start_flag, finish_flag
    global idx_pool, idx_twin

    file_animate = open("output_animate.txt", "w")
    file_animate.write("output_animate.txt opened.\n")

    while True:
        if start_flag == True:  break

    time.sleep(0.5)

    num_mode = theBridge.num_mode
    x = theBridge.x
    num_x = len(x)
    modeShapes = theBridge.modeShapeList

    anim = animation.FuncAnimation(fig, UpdateAnimate, init_func=InitAnimate,
                                   fargs=(num_mode, num_x, x, modeShapes, lock,), interval=3, blit=False)

    plt.show()


def MasterController():
    global vehicle_dict, theBridge
    global idx_twin, idx_pool, time_ref, delay_min, time_boundary, time_length, time_window, num_seg_per_time_window
    global echo_flag_monitor, echo_flag_manager, echo_flag_schedul, echo_flag_analyst
    global t_pool, A_pool, num_pool, idx_pool, idx_twin


    #    echo_flag_monitor = True
    #    echo_flag_manager = True
    #    echo_flag_schedul = True
    echo_flag_analyst = True

    theBridge = bridge.Bridge("A_bridge")  # 生成桥梁
    theBridge.SetSegmentNumber(100)  # 缺省128段
    theBridge.ModeAnalyze(3)  # 缺省3阶模态分析

    num_mode = theBridge.num_mode  # 取模态数

    #        omg = theBridge.omegaList[-1]                    # 最高阶模态频率
    #        period = 2.0*np.pi/omg                           # 最高阶模态周期
    #        t_num = int(time_length/period*100.0) + 1

    t_num = num_seg_per_time_window  # 时间窗分段数

    # 为数据池配置空间
    t_pool = [0.0] * (t_num * num_pool)  # 矢量 t_pool，num_pool*t_num 维
    A_pool = [[0.0 for col in range(num_mode)] for row in
              range(t_num * num_pool)]  # 矩阵 A_pool，num_pool*t_num 行，num_mode列

    print "theBridge.omegaList = ", theBridge.omegaList
    print "theBridge.zetaList  = ", theBridge.zetaList

    time_cond = threading.Condition()
    dict_lock = threading.Lock()

    manager = Manager(time_cond, dict_lock)
    monitor = Monitor(time_cond, dict_lock)
    schedul = Schedul(time_cond, dict_lock)
    analyst = Analyst(time_cond, dict_lock)

    manager.start()
    monitor.start()
    schedul.start()
    analyst.start()

    #    ShowAnimate(dict_lock)

    manager.join()
    monitor.join()
    schedul.join()
    analyst.join()


MasterController()

