import numpy as np
import matplotlib.pyplot as plt


s = np.random.poisson(5, 10000)
count, bins, ignored = plt.hist(s, 14, density=True)
plt.savefig("output/test2.png")
plt.show()
