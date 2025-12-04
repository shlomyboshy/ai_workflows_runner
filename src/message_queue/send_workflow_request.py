"""
Simple script to send workflow requests to RabbitMQ queue
"""
import json
import sys
import uuid
import pika
from datetime import datetime


def send_workflow_request(workflow_name: str, call_transcript: str, rabbitmq_host: str = 'localhost'):
    """
    Send a workflow execution request to RabbitMQ

    Args:
        workflow_name: Name of the workflow to execute
        call_transcript: Transcript of the patient call
        rabbitmq_host: RabbitMQ host address
    """
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
        channel = connection.channel()
        channel.queue_declare(queue='workflow_requests', durable=True)
        request_id = str(uuid.uuid4())
        message = {"workflow_name": workflow_name,
                   "call_transcript": call_transcript,
                   "request_id": request_id,
                   "timestamp": datetime.utcnow().isoformat()}
        channel.basic_publish(
            exchange='',
            routing_key='workflow_requests',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                content_type='application/json'
            )
        )
        print("Sent workflow request")
        connection.close()
        return request_id

    except pika.exceptions.AMQPConnectionError as e:
        print(f"Failed to connect to RabbitMQ at {rabbitmq_host}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error sending request: {e}")
        sys.exit(1)


def listen_for_response(request_id: str, rabbitmq_host: str = 'localhost', timeout: int = 60):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
        channel = connection.channel()
        channel.queue_declare(queue='workflow_responses', durable=True)
        print(f"\n Listening for response (timeout: {timeout}s)...")
        def callback(ch, method, properties, body):
            response = json.loads(body.decode('utf-8'))
            if response.get('request_id') == request_id:
                print(f"Received response:")
                print(json.dumps(response, indent=2))
                ch.stop_consuming()
        channel.basic_consume(
            queue='workflow_responses',
            on_message_callback=callback,
            auto_ack=True
        )
        connection.call_later(timeout, lambda: channel.stop_consuming())
        channel.start_consuming()
        connection.close()
    except Exception as e:
        print(f"Error listening for response: {e}")


def main():
    workflow_name = "patient_call_analysis_flow"
    sample_call_transcript = """
    Nurse: Hello, this is Nurse Sarah calling from the clinic. May I speak with the patient?
    Patient: Yes, this is John speaking. Patient ID 12345.
    Nurse: Thank you John. I'm calling to follow up on your recent appointment. How are you feeling?
    Patient: I'm still having some pain, it's quite frustrating actually.
    Nurse: I understand. Based on what you're describing, I think we should schedule a home visit for a more thorough examination.
    Patient: That would be helpful, thank you.
    Nurse: Great, we'll arrange that. Is there anything else I can help you with today?
    Patient: No, that's all. Thank you for calling.
    Nurse: You're welcome. Take care!
    """
    request_id = send_workflow_request(workflow_name, sample_call_transcript)
    listen_for_response(request_id)

if __name__ == "__main__":
    main()
