from flask import Flask, render_template, request
import plotly.graph_objects as go
import plotly.io as pio
from collections import defaultdict

app = Flask(__name__)

def calculate_cpm(activities, durations, predecessors):
    activity_dict = {}
    for i in range(len(activities)):
        activity_dict[activities[i]] = {
            'duration': int(durations[i]),
            'predecessors': predecessors[i].split(',') if predecessors[i] else [],
            'earliest_start': 0,
            'earliest_finish': 0,
            'latest_start': float('inf'),
            'latest_finish': float('inf')
        }

    # Forward pass
    for activity in activity_dict:
        if not activity_dict[activity]['predecessors']:
            activity_dict[activity]['earliest_start'] = 0
            activity_dict[activity]['earliest_finish'] = activity_dict[activity]['duration']
        else:
            es_times = [activity_dict[p]['earliest_finish'] for p in activity_dict[activity]['predecessors']]
            activity_dict[activity]['earliest_start'] = max(es_times)
            activity_dict[activity]['earliest_finish'] = activity_dict[activity]['earliest_start'] + activity_dict[activity]['duration']

    all_activities = list(activity_dict.keys())
    # Backward pass
    for activity in reversed(all_activities):
        if activity_dict[activity]['latest_finish'] == float('inf'):
            activity_dict[activity]['latest_finish'] = activity_dict[activity]['earliest_finish']
        activity_dict[activity]['latest_start'] = activity_dict[activity]['latest_finish'] - activity_dict[activity]['duration']
        for p in activity_dict[activity]['predecessors']:
            activity_dict[p]['latest_finish'] = min(activity_dict[p]['latest_finish'], activity_dict[activity]['latest_start'])
            activity_dict[p]['latest_start'] = activity_dict[p]['latest_finish'] - activity_dict[p]['duration']

    critical_path = []
    for activity in activity_dict:
        if activity_dict[activity]['earliest_start'] == activity_dict[activity]['latest_start']:
            critical_path.append(activity)

    return critical_path, activity_dict

def create_network_diagram(activity_dict, critical_path):
    fig = go.Figure()

    # Calculate depth of each activity
    depth = {activity: 0 for activity in activity_dict}
    for activity in activity_dict:
        for predecessor in activity_dict[activity]['predecessors']:
            depth[activity] = max(depth[activity], depth[predecessor] + 1)

    # Define unique positions for nodes
    levels = defaultdict(list)
    for activity, d in depth.items():
        levels[d].append(activity)

    # Arrange nodes by level
    y_positions = {}
    x_positions = defaultdict(int)
    for level, activities in levels.items():
        for i, activity in enumerate(activities):
            y_positions[activity] = -level  # Negative to ensure top to bottom ordering
            x_positions[level] += 1

    # Adjust x-coordinates to avoid overlapping
    for level, count in x_positions.items():
        step = 5  # Reduced step size for smaller diagram
        start = -((count - 1) * step) // 2
        for i, activity in enumerate(levels[level]):
            y_positions[activity] = start + i * step

    # Adding nodes and edges
    for activity, details in activity_dict.items():
        is_critical = activity in critical_path
        fig.add_trace(go.Scatter(
            x=[details['earliest_start']],
            y=[y_positions[activity]],
            text=[activity],
            mode='markers+text',
            marker=dict(size=20, color='red' if is_critical else 'blue'),  # Reduced node size
            textposition='top center',
            hoverinfo='text',
            hovertext=f"ES: {details['earliest_start']}<br>EF: {details['earliest_finish']}<br>LS: {details['latest_start']}<br>LF: {details['latest_finish']}"
        ))

        for predecessor in details['predecessors']:
            pred_es = activity_dict[predecessor]['earliest_start']
            pred_y = y_positions[predecessor]
            line_color = 'red' if (predecessor in critical_path and activity in critical_path) else 'black'
            fig.add_trace(go.Scatter(
                x=[pred_es, details['earliest_start']],
                y=[pred_y, y_positions[activity]],
                mode='lines',
                line=dict(color=line_color, width=2 if line_color == 'red' else 1),
                hoverinfo='none'
            ))

    fig.update_layout(
        title='Network Diagram for CPM',
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        autosize=False,
        width=800,  # Reduced width
        height=600  # Reduced height
    )

    network_html = pio.to_html(fig, full_html=False)
    return network_html

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    activities = request.form.getlist('activities')
    durations = request.form.getlist('durations')
    predecessors = request.form.getlist('predecessors')

    if len(activities) == len(durations) == len(predecessors):
        cpm_result, activity_details = calculate_cpm(activities, durations, predecessors)
        network_diagram_html = create_network_diagram(activity_details, cpm_result)
        return render_template('result.html', result=cpm_result, details=activity_details, network_diagram=network_diagram_html, activities=activities, durations=durations, predecessors=predecessors, zip=zip)
    else:
        return "Error: Mismatch in input lengths."

if __name__ == '__main__':
    app.run(debug=True)
