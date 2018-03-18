# coding: utf-8

import bridge
import numpy as np
# v_slow        = 200.0/9.0  # m/s
# v_fast        = 250.0/9.0  # m/s # 高速公路、干线一级公路设计速度100km/h,地质地形条件受限时采用80km/h

v_slow = 20  # 取简化值
v_fast = 25  # 取简化值

t_delay_slow = bridge.s_span / v_slow
t_delay_fast = bridge.s_span / v_fast

f_normal = 550000  # N # =>55t 规范
f_small = 250000  # N # 中国重汽 斯太尔M5G箱型货车 整备质量10.2t 满载质量25t 轻车(small)
f_huge = 700000  # N # 中国重汽 HOWO矿用载货车 整备质量29.3t 满载质量70t 重车(huge)


class MovingConcentrateForce:
    def __init__(self, time_stamp, direction, vehicle_type, bridge, i=0):
        if vehicle_type == "sequence":
            self.name = "SQ_" + "%02i" % (i)
            self.force = f_huge
            omg = bridge.omegaList[0]
            l = bridge.m_span
            pi = np.pi
            velo_res = omg * l / pi  # 尝试激起一阶模态的共振

            self.velocity = velo_res
            self.delay = bridge.s_span / self.velocity
        elif vehicle_type == "sequence2":
            self.name = "SQ2_" + "%02i" % (i)
            self.force = f_huge
            omg = bridge.omegaList[1]
            l = bridge.m_span
            pi = np.pi
            velo_res = 2 * omg * l / pi  # 尝试激起二阶模态的共振

            self.velocity = velo_res
            self.delay = bridge.s_span / self.velocity
        elif vehicle_type == "huge_slow":
            self.name = "HS_" + "%010.3f" % (time_stamp)
            self.force = f_huge
            self.velocity = v_slow
            self.delay = t_delay_slow
        else:  # elif vehicle_type == "small_fast":
            self.name = "SF_" + "%010.3f" % (time_stamp)
            self.force = f_small
            self.velocity = v_fast
            self.delay = t_delay_fast

        self.direction = direction

        self.bridge = bridge
        self.m_span = bridge.m_span

        self.duration = self.m_span / self.velocity

        self.time_stamp = time_stamp + i * self.duration

    def Info(self):
        return (self.name, self.time_stamp, self.delay, self.duration, self.force, self.velocity, self.direction,
                self.bridge.bridge_id)

    def OnBridgeCheck(self, time_line):  # 检查是否在桥上
        if time_line - self.time_stamp - self.delay > self.duration:  # 已离开
            return False
        if time_line - self.time_stamp - self.delay < 0:  # 未上桥
            return False
        return True  # 正在桥上

    def LeaveBridgeCheck(self, time_line):  # 检查是否离开桥
        if time_line - self.time_stamp - self.delay > self.duration:  # 已离开
            return True
        return False  # 未离开桥

    def NotReachBridgeCheck(self, time_line):  # 检查是否到达桥
        if time_line - self.time_stamp - self.delay < 0:  # 未到达
            return True
        return False  # 已到达

    def XPosition(self, time):
        x = self.velocity * (time - self.time_stamp - self.delay)
        if self.direction == "from_left":
            return x
        else:
            return self.m_span - x
