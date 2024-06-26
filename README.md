# Heat Sensor Dash App

I created this Dash app visualization dashboard as part of a course project during the Spring 2024 term.

The project stakeholders were a PhD student and his advisor at Indiana University Bloomington's Informatics Department. Our project sponsors installed heat sensor throughout the Bloomington campus, which measure temperature, relative humidity, and dew point. The "urban heat island" effect is a phenomenon where urban areas experience significantly warmer temperatures than their rural counterparts, so, with the help of these sensors, the sponsors are interested in understanding the impact of heat in urban spaces. The sensors were placed in locations of varying exposure to radiation; e.g., a shaded area by a river, an open parking lot, a field, etc.

There were a few project objectives; among them was to enhance an existing dashboard with interactive features. This was my focus. Through this project, I learned how to create visualizations with Python's Plotly and Dash libraries. Per the sponsors' requests, I implemented the following features:

- Interactivity between the map and the time series chart so that if the user clicks on a sensor location (or multiple locations), the time series chart will plot only the selected sensor’s data points.
- Interactivity works smoothly with different parameter inputs.
- A color schema to the sensor map points based on their temperatures averaged over the selected date range.
- More aggregate metrics. Previously, there were only weekly, daily, and hourly averages in addition to the raw 5-min sensor readings. I added 12-hr, 6-hr, 3-hr, and 3-hr averages.
- An option to view rolling averages (window of 4 units).

This GitHub repo contains my code for this dashboard, which can be viewed [here](https://heat-sensor-dash-app.onrender.com), deployed via Render.

Due to GitHub's limited file upload size, the sensor data uploaded to this repo is a snippet of the actual dataset that I worked with. The truncated data contains readings from May - Sep. of 2023. Despite the smaller data size, **some changes to the dashboard's inputs may take a minute or two to update the time series chart, particularly the aggregates that are more granular than the daily average.**
