# coding: utf-8

import numpy as np

m_span = 50.0  # m 主跨
s_span = 50.0  # m 边跨
E = 36500000000  # Pa # C65混凝土
I = 1.24  # m^4 # T形，上翼缘宽度3.5m，梁高3.3m，翼缘厚0.2m，腹板厚0.25m
m = 148600.0 / 25  # kg/m # (3.5*0.2+2.1*0.2)*50*26.0/9.8 # 预应力混凝土重力密度 26kN/m^3
damp_c = 50000


class Bridge:
    def __init__(self, bridge_id="", m_span=m_span, s_span=s_span, EI=E * I, m=m, damp_c=damp_c):
        self.bridge_id = bridge_id
        self.m_span = m_span  # 中跨
        self.s_span = s_span  # 左右边跨
        self.EI = EI
        self.m = m
        self.damp_c = damp_c
        self.num_mode = 0

        self.omegaList = []  # 模态固有频率列表
        self.zetaList = []  # 模态阻尼比列表
        self.modeShapeList = []  # 模态向量列表（每个元素也是列表，维数与坐标维数一致）
        self.x = None

    def SetSegmentNumber(self, num_segment=128):
        self.x = np.linspace(0, self.m_span, num_segment)

    def ModeAnalyze(self, num_mode=3):
        self.num_mode = num_mode
        for i in range(1, num_mode + 1):
            omega = (i * np.pi / self.m_span) * (i * np.pi / self.m_span) * np.sqrt(self.EI / self.m)
            self.omegaList.append(omega)

            zeta = self.damp_c / self.m / 2.0 / omega
            self.zetaList.append(zeta)

            y = np.sin(i * np.pi * self.x / self.m_span)
            self.modeShapeList.append(y)
