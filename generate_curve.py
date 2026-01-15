import matplotlib.pyplot as plt
import os

def createCurve(center, upper, lower, fig=None, ax=None, isSave=False, name="Kurve"):
    do_show = True
    if ax and fig:
        do_show = False
        ax.cla()

    x_labels = ['Bund', '0.075', '0.125', '0.25', '0.5', '1', '2', '4', '8', '16']
    y_labels = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    # Define numerical x positions for plotting
    x_positions = range(len(x_labels))

    # Create a figure and an axes object
    if not ax or not fig:
        fig, ax = plt.subplots(figsize=(6, 4))

    # Plot the two lines with different thicknesses, both in red
    ax.plot(x_positions, center, color='red', linewidth=2, marker='o', markerfacecolor='yellow', markeredgecolor='red', markersize=4, zorder=5)
    ax.plot(x_positions, upper, color='red', linewidth=1)
    ax.plot(x_positions, lower, color='red', linewidth=1)

    # Set the x-axis and y-axis tick locations and labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, rotation=45)
    ax.set_yticks(y_labels)
    ax.set_yticklabels(y_labels)
    
    # Set the x-axis limits to start at 0 (Bund) and end at 9 (16)
    ax.set_xlim(x_positions[0], x_positions[-1])
    ax.set_ylim(0, 100)

    # Add a grid to the plot
    ax.grid(True)

    # Set labels for the axes and a title for the plot
    ax.set_xlabel('Maskevidde i mm')
    ax.set_ylabel('Gennemfald i %')
    ax.set_title(name)

    # Ensure the labels do not overlap
    fig.tight_layout()

    if not isSave:
        if do_show:
            fig.show()
        else:
            fig.canvas.draw()
            fig.canvas.flush_events()
    else:
        os.makedirs("pdf", exist_ok=True)
        fig.savefig("pdf\\graph.svg", format='svg')

    return fig, ax