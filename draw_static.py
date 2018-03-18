# coding: utf-8

from matplotlib import pyplot as plt

f = open('output_analyst.txt', 'r')

data_lines = f.readlines()
num_line = len(data_lines) - 2

t = [0.0 for i in range(num_line)]
A1 = [0.0 for i in range(num_line)]
A2 = [0.0 for i in range(num_line)]
A3 = [0.0 for i in range(num_line)]

for i in range(num_line):
    data_line = data_lines[i + 1]
    (t_, A1_, A2_, A3_) = eval(data_line)
    t[i] = t_
    A1[i] = -A1_
    A2[i] = -A2_
    A3[i] = -A3_
# (t[i], A1[i], A2[i], A3[i]) = eval(data_line)

f.close()
print "num_line =%6i" % num_line
print "(t0, t1) =(%9.3f, %9.3f)" % (t[0], t[num_line - 1])
print t
print A1

# figure()
plt.plot(t, A1, 'r', t, A2, 'b', t, A3, 'k')
plt.xlabel('time(sec)')
plt.ylabel('mode responses(m)')
plt.show()
