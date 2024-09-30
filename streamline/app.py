from flask import Flask, render_template, request, redirect, url_for
import folium
import pandas as pd
import uuid
import math
from datetime import timedelta, datetime

app = Flask(__name__)

# Load your data
data = pd.read_csv('streamline - Sheet1.csv')

# Function to generate a unique consignment number
def generate_consignment_number():
    return str(uuid.uuid4())[:8]

# Function to calculate distance between two coordinates using Haversine formula
def calculate_distance(coord1, coord2):
    R = 6371.0  # Radius of the Earth in kilometers
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Distance in kilometers
    distance = R * c
    return distance

# Function to estimate time to travel a certain distance at a given speed
def estimate_time(distance_km, speed_kmph=50):
    return distance_km / speed_kmph  # Return time in hours

# Function to calculate the estimated delivery date based on travel time
def estimate_delivery_date(total_hours):
    current_datetime = datetime.now()
    estimated_datetime = current_datetime + timedelta(hours=total_hours)
    return estimated_datetime.strftime('%Y-%m-%d %H:%M:%S')  # Return in readable format

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        sender = request.form['sender']
        receiver = request.form['receiver']
        
        # Generate a unique consignment number
        consignment_number = generate_consignment_number()
        
        # Redirect to map view with sender, receiver, and consignment number
        return redirect(url_for('map_view', consignment_number=consignment_number, sender=sender, receiver=receiver))

    return render_template('create_consignment.html')

@app.route('/map/<consignment_number>/<sender>/<receiver>', methods=['GET'])
def map_view(consignment_number, sender, receiver):
    map_html = ""
    route_info = []
    total_time = 0
    final_office_name = ""

    # Get mapping information
    map_html, route_info, final_office_name, total_time = map_with_estimated_time(sender, receiver, consignment_number)

    # Calculate estimated delivery date
    estimated_delivery_date = estimate_delivery_date(total_time)

    return render_template('map_with_info.html', map_html=map_html, route_info=route_info,
                           final_office_name=final_office_name, total_time=total_time,
                           estimated_delivery_date=estimated_delivery_date,
                           consignment_number=consignment_number)

def map_with_estimated_time(sender, receiver, consignment_number):
    # Get the coordinates of sender and receiver
    sender_office = data[data['OfficeName'] == sender]
    receiver_office = data[data['OfficeName'] == receiver]

    if sender_office.empty or receiver_office.empty:
        return None, None, None, 0  # Handle case where office does not exist

    sender_coords = (sender_office.iloc[0]['Latitude'], sender_office.iloc[0]['Longitude'])
    receiver_coords = (receiver_office.iloc[0]['Latitude'], receiver_office.iloc[0]['Longitude'])

    # Create a map centered on India
    route_map = folium.Map(location=[20.5937, 78.9629], zoom_start=5, max_bounds=True)
    route_map.fit_bounds([[6.4627, 68.1097], [35.5087, 97.3954]])

    total_time = 0
    route_info = []

    # Adding all offices to the map
    for _, office in data.iterrows():
        office_coords = (office['Latitude'], office['Longitude'])
        folium.Marker(
            location=office_coords,
            popup=f"{office['OfficeName']}<br>Latitude: {office['Latitude']}<br>Longitude: {office['Longitude']}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(route_map)

    # Adding the sender marker
    folium.Marker(
        location=sender_coords,
        popup=f"Sender: {sender}",
        icon=folium.Icon(color='yellow', icon='info-sign')
    ).add_to(route_map)

    # Adding the receiver marker
    folium.Marker(
        location=receiver_coords,
        popup=f"Receiver: {receiver}",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(route_map)

    # Get all offices between sender and receiver
    office_names = data['OfficeName'].tolist()
    start_index = office_names.index(sender)
    end_index = office_names.index(receiver)

    # Loop through the offices from sender to receiver
    for i in range(start_index, end_index + 1):
        current_office = data.iloc[i]
        current_coords = (current_office['Latitude'], current_office['Longitude'])
        
        if i > start_index:  # Not the first office
            # Calculate distance and estimated time from the previous office to the current office
            previous_office = data.iloc[i - 1]
            previous_coords = (previous_office['Latitude'], previous_office['Longitude'])
            distance_km = calculate_distance(previous_coords, current_coords)
            time_hours = estimate_time(distance_km)
            total_time += time_hours
            
            # Draw line between previous office and current office
            folium.PolyLine([previous_coords, current_coords], color="blue", weight=2.5, opacity=1).add_to(route_map)

            # Add route info for this segment
            route_info.append({
                "current_office": previous_office['OfficeName'],
                "next_office": current_office['OfficeName'],
                "distance": round(distance_km, 2),
                "time": round(time_hours, 2)
            })

    # Add the receiver's office marker
    folium.Marker(
        location=receiver_coords,
        popup=f"Final Stop: {receiver}<br>Consignment No: {consignment_number}",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(route_map)

    map_html = route_map._repr_html_()

    return map_html, route_info, receiver, round(total_time, 2)

if __name__ == "__main__":
    app.run(debug=True)
