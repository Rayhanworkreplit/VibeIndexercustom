import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Parse the architecture data
data = {
  "architecture_layers": [
    {
      "layer": "Input Sources",
      "components": [
        {"name": "URL Lists", "description": "Manual URL input, CSV files, database imports"},
        {"name": "Sitemap Parse", "description": "XML sitemap extraction and processing"},
        {"name": "Backlink Disc", "description": "Automated backlink discovery and collection"}
      ]
    },
    {
      "layer": "Processing Engine",
      "components": [
        {"name": "URL Queue Mgr", "description": "Priority-based queuing system"},
        {"name": "Rate Limiter", "description": "Anti-detection rate limiting"},
        {"name": "Proxy Rotator", "description": "IP rotation for anonymity"}
      ]
    },
    {
      "layer": "Multi-Method Indexing",
      "components": [
        {"name": "Social Bookmark", "description": "Automated submissions to bookmarking sites"},
        {"name": "RSS Feed Dist", "description": "RSS feed creation and syndication"},
        {"name": "Web 2.0 Auto", "description": "Blogger, WordPress, Tumblr automation"},
        {"name": "Forum Comment", "description": "Strategic forum and blog commenting"},
        {"name": "Dir Submission", "description": "Web directory submission automation"},
        {"name": "Social Signal", "description": "Social media sharing automation"}
      ]
    },
    {
      "layer": "Browser Automation",
      "components": [
        {"name": "Selenium Grid", "description": "Distributed browser automation"},
        {"name": "Headless Brows", "description": "Chrome/Firefox headless instances"},
        {"name": "User-Agent Rot", "description": "Browser fingerprint randomization"}
      ]
    },
    {
      "layer": "Monitor & Valid",
      "components": [
        {"name": "SERP Checking", "description": "Google search result verification"},
        {"name": "Link Verify", "description": "Backlink status monitoring"},
        {"name": "Success Track", "description": "Indexing success rate analytics"}
      ]
    },
    {
      "layer": "Storage & Analytics",
      "components": [
        {"name": "Database Layer", "description": "PostgreSQL/MySQL data storage"},
        {"name": "Analytics Dash", "description": "Performance metrics and reports"},
        {"name": "Retry Queue", "description": "Failed URL re-processing system"}
      ]
    }
  ]
}

# Create the flowchart using shapes and annotations
fig = go.Figure()

# Layer colors and positions with more vertical spacing
colors = ['#1FB8CD', '#DB4545', '#2E8B57', '#5D878F', '#D2BA4C', '#B4413C']
layer_y_positions = [7, 5.5, 4, 2.5, 1, -0.5]

# Draw components and layer backgrounds
for layer_idx, layer in enumerate(data['architecture_layers']):
    layer_name = layer['layer']
    components = layer['components']
    y_pos = layer_y_positions[layer_idx]
    color = colors[layer_idx]
    
    # Calculate component positions horizontally with better spacing
    num_components = len(components)
    if num_components <= 3:
        x_positions = [i * 2.5 + 1 for i in range(num_components)]
    else:
        # For Multi-Method Indexing layer with 6 components
        x_positions = [i * 1.3 + 0.5 for i in range(num_components)]
    
    max_x = max(x_positions) + 1 if x_positions else 3
    
    # Add layer background with better contrast
    fig.add_shape(
        type="rect",
        x0=-1.5,
        y0=y_pos - 0.6,
        x1=max_x,
        y1=y_pos + 0.6,
        line=dict(color=color, width=3),
        fillcolor=color,
        opacity=0.15,
        layer="below"
    )
    
    # Add layer title with better positioning
    fig.add_annotation(
        x=-2,
        y=y_pos,
        text=layer_name,
        showarrow=False,
        font=dict(size=14, color=color, family="Arial Black"),
        textangle=-90,
        xanchor="center",
        yanchor="middle"
    )
    
    # Add components with larger boxes
    for comp_idx, component in enumerate(components):
        x_pos = x_positions[comp_idx]
        comp_name = component['name']
        
        # Add component box - larger size
        fig.add_shape(
            type="rect",
            x0=x_pos - 0.6,
            y0=y_pos - 0.25,
            x1=x_pos + 0.6,
            y1=y_pos + 0.25,
            line=dict(color=color, width=2),
            fillcolor=color,
            opacity=0.9
        )
        
        # Add component text with larger font
        fig.add_annotation(
            x=x_pos,
            y=y_pos,
            text=comp_name,
            showarrow=False,
            font=dict(size=11, color="white", family="Arial"),
            xanchor="center",
            yanchor="middle"
        )

# Add more visible flow arrows between layers
for i in range(len(data['architecture_layers']) - 1):
    y_start = layer_y_positions[i] - 0.6
    y_end = layer_y_positions[i + 1] + 0.6
    x_arrow = 4
    
    # Add arrow shaft
    fig.add_shape(
        type="line",
        x0=x_arrow,
        y0=y_start,
        x1=x_arrow,
        y1=y_end + 0.2,
        line=dict(color="#333333", width=4)
    )
    
    # Add arrowhead
    fig.add_shape(
        type="line",
        x0=x_arrow - 0.15,
        y0=y_end + 0.35,
        x1=x_arrow,
        y1=y_end + 0.2,
        line=dict(color="#333333", width=4)
    )
    fig.add_shape(
        type="line",
        x0=x_arrow + 0.15,
        y0=y_end + 0.35,
        x1=x_arrow,
        y1=y_end + 0.2,
        line=dict(color="#333333", width=4)
    )

# Add invisible scatter points for legend with full names
for i, layer in enumerate(data['architecture_layers']):
    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='markers',
        marker=dict(size=15, color=colors[i]),
        name=layer['layer'],
        showlegend=True
    ))

# Update layout with better spacing
fig.update_layout(
    title="Backlink Indexer Architecture",
    xaxis=dict(
        range=[-3, 9],
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title=""
    ),
    yaxis=dict(
        range=[-1.5, 8],
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title=""
    ),
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5),
    plot_bgcolor='white'
)

# Save the chart
fig.write_image("backlink_indexer_flowchart.png", width=1600, height=1000, scale=2)