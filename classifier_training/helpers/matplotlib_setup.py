from matplotlib import pyplot as plt

#plt.style.use("seaborn-bright")
plt.style.use("seaborn-v0_8-colorblind")
plt.rcParams["figure.figsize"] = (14, 8)


# Set font sizes for different plot elements
plt.rcParams["axes.titlesize"] = 24  # Title font size
plt.rcParams["axes.labelsize"] = 22  # Axis title font size
plt.rcParams["xtick.labelsize"] = 18  # X-axis tick label font size
plt.rcParams["ytick.labelsize"] = 18  # Y-axis tick label font size
plt.rcParams["legend.fontsize"] = 20  # Legend font size

plt.rcParams["axes.grid"] = True  # Enable grid

# Set default line width for plots
plt.rcParams["lines.linewidth"] = 3

