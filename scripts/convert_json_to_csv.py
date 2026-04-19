import json
import csv
from datetime import datetime
import os

input_file = 'data/raw/sample.json'
output_file = 'data/raw_2025-04-01.csv'

def convert():
    print(f"Reading from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    print(f"Writing to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['datetime', 'vehicle', 'lng', 'lat', 'speed', 'driver', 'door_up', 'door_down'])
        
        count = 0
        for item in data:
            if 'msgBusWayPoint' in item:
                wp = item['msgBusWayPoint']
                
                # Convert unix timestamp to string format "YYYY-MM-DD HH:MM:SS"
                dt = ""
                if 'datetime' in wp:
                    try:
                        dt = datetime.fromtimestamp(wp['datetime']).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        dt = wp['datetime']
                
                writer.writerow([
                    dt,
                    wp.get('vehicle', ''),
                    wp.get('x', ''),
                    wp.get('y', ''),
                    wp.get('speed', ''),
                    wp.get('driver', ''),
                    wp.get('door_up', 'False'),
                    wp.get('door_down', 'False')
                ])
                count += 1
                
        print(f"Successfully converted {count} records to {output_file}.")

if __name__ == '__main__':
    convert()
