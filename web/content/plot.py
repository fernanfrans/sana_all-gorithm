import plotly.graph_objects as go

# Sample data
x = [1, 2, 3, 4, 5]
y = [10, 15, 13, 17, 14]

# Create figure
fig = go.Figure()

# Add line plot
fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='Line Plot'))

# Add title and labels
fig.update_layout(
    title='Simple Plotly Line Plot',
    xaxis_title='X Axis',
    yaxis_title='Y Axis'
)

# Show plot
fig.show()
