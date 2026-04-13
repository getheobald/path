import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot_convergence(scores):
    iterations = range(len(scores))

    plt.plot(iterations, scores)
    plt.xlabel("Iteration")
    plt.ylabel("Score")
    plt.title("Convergence Plot")
    plt.grid(True)

    plt.savefig('visualizations/convergence_plot.png')