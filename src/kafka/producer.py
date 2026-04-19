import json
import csv
import sys
import time
from confluent_kafka import Producer

# =============================================================================
# PRODUCER CONFIGURATION
# =============================================================================

conf = {
    'bootstrap.servers': 'localhost:9092',
    'enable.idempotence': True,
    'acks': 'all',
    'retries': 3,
    'max.in.flight.requests.per.connection': 5,
    'linger.ms': 5,
    'batch.size': 64 * 1024,
    'compression.type': 'lz4',
    'message.timeout.ms': 15000,
    'delivery.timeout.ms': 30000,
}

producer = Producer(conf)


def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")


def send_async(producer, topic, key, value):
    try:
        producer.produce(
            topic=topic,
            key=key,
            value=value,
            callback=delivery_report,
        )
        return True
    except BufferError:
        print("Buffer full, polling...")
        producer.poll(0.5)
        return False
    except Exception as exc:  # Log unexpected issues
        print(f"Send error: {exc}")
        return False


def process_csv_to_kafka(csv_file_path, topic='bus-gps-tracking', max_records=None):
    print(f"Processing: {csv_file_path}")
    print(f"Sending to Topic: {topic}")
    print(f"Max Records: {max_records if max_records else 'Unlimited'}")

    sent_count = 0
    failed_count = 0
    total_count = 0

    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)

            if 'datetime' not in csv_reader.fieldnames:
                print(f"ERROR: Column 'datetime' not found. Found: {csv_reader.fieldnames}")
                return {
                    'total': 0,
                    'sent': 0,
                    'failed': 0,
                    'success_rate': 0,
                }

            for row in csv_reader:
                total_count += 1

                try:
                    bus_data = {
                        'datetime': row['datetime'],
                        'vehicle': row['vehicle'],
                        'lng': float(row['lng']) if row.get('lng') and row['lng'].strip() else None,
                        'lat': float(row['lat']) if row.get('lat') and row['lat'].strip() else None,
                        'speed': float(row['speed']) if row.get('speed') and row['speed'].strip() else None,
                        'driver': row.get('driver'),
                        'door_up': str(row.get('door_up')).lower() == 'true',
                        'door_down': str(row.get('door_down')).lower() == 'true',
                    }

                    success = send_async(
                        producer=producer,
                        topic=topic,
                        key=row['vehicle'],
                        value=json.dumps(bus_data),
                    )

                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1

                except Exception as exc:  # Skip bad records but continue stream
                    print(f"Row {total_count} error: {exc}")
                    failed_count += 1

                if total_count % 5000 == 0:
                    producer.poll(0)
                    print(f"Progress: {sent_count:,} sent")

                if max_records and total_count >= max_records:
                    print(f"Reached limit: {max_records}")
                    break

        print("Flushing remaining messages...")
        remaining = producer.flush(30)

        if remaining > 0:
            failed_count += remaining

    except FileNotFoundError:
        print(f"File not found: {csv_file_path}")
        return {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'success_rate': 0,
        }
    except Exception as exc:
        print(f"Error: {exc}")
        return {
            'total': total_count,
            'sent': sent_count,
            'failed': failed_count,
            'success_rate': 0,
        }

    success_rate = (sent_count / total_count * 100) if total_count else 0
    print(
        f"COMPLETED! Total: {total_count:,}, Sent: {sent_count:,}, Failed: {failed_count:,}, "
        f"Success: {success_rate:.1f}%"
    )

    return {
        'total': total_count,
        'sent': sent_count,
        'failed': failed_count,
        'success_rate': success_rate,
    }


if __name__ == "__main__":
    test_file = "data/raw_2025-04-01.csv"
    limit = None

    if len(sys.argv) > 1:
        test_file = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            print("Limit must be an integer")

    print("KAFKA PRODUCER TEST")
    print(f"File: {test_file}")

    result = process_csv_to_kafka(
        csv_file_path=test_file,
        topic='bus-gps-tracking',
        max_records=limit,
    )

    if result['success_rate'] >= 90:
        print("TEST PASSED! Producer is working well.")
    elif result['success_rate'] >= 70:
        print("TEST OK but has some issues.")
    else:
        print("TEST FAILED! Check Kafka connection.")
        sys.exit(1)
